"""Small, fail-closed Open-Meteo adapter; never substitutes invented weather."""

from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from math import isfinite
from threading import Lock
from time import monotonic
from typing import Annotated

import requests
from pydantic import BaseModel, ConfigDict, Field, field_validator

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_TIMEZONE = "Europe/Istanbul"
FORECAST_DAYS = 7
CACHE_TTL_SECONDS = 900
CACHE_MAX_ENTRIES = 256
REQUEST_TIMEOUT = (3.05, 10)
# Istanbul has used UTC+03 throughout the supported, current forecast period.
# This avoids depending on OS IANA tzdata availability on Windows.
ISTANBUL = timezone(timedelta(hours=3), name=FORECAST_TIMEZONE)


class WeatherUnavailable(RuntimeError):
    """Weather could not be fetched or did not satisfy the forecast contract."""


class ForecastDay(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    date: date
    et0_mm: Annotated[float, Field(strict=True, ge=0, le=100, allow_inf_nan=False)]
    rain_mm: Annotated[float, Field(strict=True, ge=0, le=1000, allow_inf_nan=False)]

    @field_validator("date", mode="before")
    @classmethod
    def iso_date(cls, value):
        if type(value) is date:
            return value
        if not isinstance(value, str):
            raise ValueError("date must be YYYY-MM-DD")
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("date must be YYYY-MM-DD")
        return parsed


_cache: OrderedDict[tuple[float, float, date], tuple[float, tuple[ForecastDay, ...]]] = OrderedDict()
_cache_lock = Lock()


def local_today() -> date:
    return datetime.now(ISTANBUL).date()


def _parse_forecast(payload, start: date) -> tuple[ForecastDay, ...]:
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError("invalid forecast object")
    if payload.get("timezone") != FORECAST_TIMEZONE:
        raise ValueError("invalid forecast timezone")
    units = payload.get("daily_units")
    if not isinstance(units, dict) or any(
        units.get(name) != "mm" for name in ("et0_fao_evapotranspiration", "rain_sum")
    ):
        raise ValueError("forecast units must be mm")
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise ValueError("missing daily forecast")
    arrays = [daily.get(name) for name in ("time", "et0_fao_evapotranspiration", "rain_sum")]
    if any(not isinstance(values, list) or len(values) != FORECAST_DAYS for values in arrays):
        raise ValueError("forecast must contain seven complete days")
    days = tuple(
        ForecastDay(date=day, et0_mm=et0, rain_mm=rain)
        for day, et0, rain in zip(*arrays)
    )
    if any(day.date != start + timedelta(days=i) for i, day in enumerate(days)):
        raise ValueError("forecast dates must start today and be consecutive")
    return days


def get_forecast(latitude: float, longitude: float) -> tuple[ForecastDay, ...]:
    """Return exactly seven validated days, cached by exact coordinates/local date.

    Expired entries are never served, including during an upstream outage.
    Frozen rows and a tuple prevent callers from modifying cached data.
    """
    for value, limit in ((latitude, 90), (longitude, 180)):
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise ValueError("coordinates must be numbers")
        if not isfinite(value) or not -limit <= value <= limit:
            raise ValueError("coordinates out of range")
    today = local_today()
    key = (latitude, longitude, today)
    now = monotonic()
    with _cache_lock:
        for old_key, (expires, _) in list(_cache.items()):
            if expires <= now or old_key[2] != today:
                del _cache[old_key]
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key][1]

    try:
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": "et0_fao_evapotranspiration,rain_sum",
                "timezone": FORECAST_TIMEZONE,
                "forecast_days": FORECAST_DAYS,
                "precipitation_unit": "mm",
            },
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        # Redirects must not change the fixed upstream destination.
        if response.status_code != 200:
            raise WeatherUnavailable("Weather provider returned an unsuccessful response.")
        days = _parse_forecast(response.json(), today)
    except (requests.RequestException, ValueError, TypeError, OverflowError) as exc:
        raise WeatherUnavailable("Weather forecast is unavailable or invalid.") from exc

    # A response crossing midnight is no longer a current seven-day forecast.
    if local_today() != today:
        raise WeatherUnavailable("Weather forecast crossed the local date boundary; retry.")
    with _cache_lock:
        _cache[key] = (monotonic() + CACHE_TTL_SECONDS, days)
        _cache.move_to_end(key)
        while len(_cache) > CACHE_MAX_ENTRIES:
            _cache.popitem(last=False)
    return days
