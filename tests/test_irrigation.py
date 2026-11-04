from datetime import date, timedelta

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import mevcut_kullanici
from app.services import weather_service as weather
from app.services.irrigation_service import IrrigationRequest, simulate_irrigation
from app.water_routes import router


def request(**overrides):
    return IrrigationRequest(**{
        'latitude': 38.4, 'longitude': 27.1, 'area_decare': 10,
        'current_deficit_mm': 10, 'allowed_deficit_mm': 15, 'kc': 1,
        **overrides,
    })


def test_threshold_volume_and_method_conversion():
    day = weather.ForecastDay(date='2026-11-05', et0_mm=5, rain_mm=0)
    result = simulate_irrigation(request(), [day], source='user')
    assert result['days'][0]['irrigation_needed']
    assert result['total_irrigation_volume_m3'] == pytest.approx(15 / .9 * 10)
    assert result['final_deficit_mm'] == 0
    surface = simulate_irrigation(request(irrigation_method='salma'), [day], source='user')
    assert surface['total_irrigation_volume_m3'] == pytest.approx(250)
    assert result['predictions_only'] and not result['auto_action']


def test_rain_offsets_deficit_without_carrying_negative_storage():
    days = [weather.ForecastDay(date='2026-11-05', et0_mm=5, rain_mm=30),
            weather.ForecastDay(date='2026-11-06', et0_mm=5, rain_mm=0)]
    result = simulate_irrigation(request(), days, source='user')
    assert result['total_irrigation_volume_m3'] == 0
    assert result['days'][0]['drainage_mm'] == 15
    assert result['final_deficit_mm'] == 5


@pytest.mark.parametrize('change', [{'latitude': 91}, {'kc': 0}, {'area_decare': float('inf')},
                                   {'current_deficit_mm': -1}, {'effective_rain_fraction': 1.1}])
def test_invalid_inputs_rejected(change):
    with pytest.raises(ValueError):
        request(**change)


def test_offline_dates_must_be_consecutive():
    with pytest.raises(ValueError):
        request(forecast=[{'date': '2026-11-05', 'et0_mm': 5, 'rain_mm': 0},
                          {'date': '2026-11-07', 'et0_mm': 5, 'rain_mm': 0}])


@pytest.fixture
def forecast_setup(monkeypatch):
    weather._cache.clear()
    today = date(2026, 11, 5)
    monkeypatch.setattr(weather, 'local_today', lambda: today)
    payload = {
        'timezone': 'Europe/Istanbul',
        'daily_units': {'et0_fao_evapotranspiration': 'mm', 'rain_sum': 'mm'},
        'daily': {'time': [(today + timedelta(days=i)).isoformat() for i in range(7)],
                  'et0_fao_evapotranspiration': [5] * 7, 'rain_sum': [0] * 7},
    }
    return payload


def test_weather_cache_and_request_contract(monkeypatch, forecast_setup):
    calls = []
    class Response:
        status_code = 200
        def json(self):
            return forecast_setup
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()
    monkeypatch.setattr(weather.requests, 'get', get)
    assert len(weather.get_forecast(38.4, 27.1)) == 7
    assert len(weather.get_forecast(38.4, 27.1)) == 7
    assert len(calls) == 1
    assert calls[0][0] == weather.FORECAST_URL
    assert calls[0][1]['timeout'] == weather.REQUEST_TIMEOUT
    assert calls[0][1]['allow_redirects'] is False
    assert calls[0][1]['params']['timezone'] == 'Europe/Istanbul'


def test_weather_invalid_units_and_timeout_fail_closed(monkeypatch, forecast_setup):
    class Response:
        status_code = 200
        def json(self):
            return {**forecast_setup, 'daily_units': {}}
    monkeypatch.setattr(weather.requests, 'get', lambda *a, **kw: Response())
    with pytest.raises(weather.WeatherUnavailable):
        weather.get_forecast(38.4, 27.1)
    def timeout(*args, **kwargs):
        raise requests.Timeout()
    monkeypatch.setattr(weather.requests, 'get', timeout)
    with pytest.raises(weather.WeatherUnavailable):
        weather.get_forecast(38.4, 27.1)
    assert not weather._cache


def test_irrigation_api_auth_offline_and_provider_failure(monkeypatch):
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    payload = request().model_dump()
    assert client.post('/sulama/oneri', json=payload).status_code == 401
    app.dependency_overrides[mevcut_kullanici] = lambda: object()
    payload['forecast'] = [{'date': '2026-11-05', 'et0_mm': 5, 'rain_mm': 0}]
    result = client.post('/sulama/oneri', json=payload)
    assert result.status_code == 200
    assert result.json()['source'] == 'user'
    assert client.get('/su/katalog').status_code == 200
    import app.water_routes as routes
    def unavailable(*args):
        raise weather.WeatherUnavailable()
    monkeypatch.setattr(routes, 'get_forecast', unavailable)
    payload['forecast'] = None
    assert client.post('/sulama/oneri', json=payload).status_code == 503
