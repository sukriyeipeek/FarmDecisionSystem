"""Pure daily root-zone deficit simulation, with user-supplied crop coefficient."""

from datetime import timedelta
from typing import Annotated, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.water_service import IRRIGATION_EFFICIENCY
from app.services.weather_service import FORECAST_TIMEZONE, ForecastDay


class IrrigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: Annotated[float, Field(strict=True, ge=-90, le=90, allow_inf_nan=False)]
    longitude: Annotated[float, Field(strict=True, ge=-180, le=180, allow_inf_nan=False)]
    area_decare: Annotated[float, Field(strict=True, gt=0, le=1_000_000, allow_inf_nan=False)]
    current_deficit_mm: Annotated[float, Field(strict=True, ge=0, le=1000, allow_inf_nan=False)]
    allowed_deficit_mm: Annotated[float, Field(strict=True, gt=0, le=1000, allow_inf_nan=False)]
    kc: Annotated[float, Field(strict=True, gt=0, le=3, allow_inf_nan=False)]
    irrigation_method: Literal["damla", "yagmurlama", "salma"] = "damla"
    effective_rain_fraction: Annotated[
        float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)
    ] = 1.0
    forecast: Annotated[list[ForecastDay], Field(min_length=1, max_length=7)] | None = None

    @field_validator("forecast")
    @classmethod
    def consecutive_days(cls, rows):
        if rows is not None and any(
            day.date != rows[0].date + timedelta(days=i) for i, day in enumerate(rows)
        ):
            raise ValueError("forecast dates must be ordered, unique and consecutive")
        return rows


def simulate_irrigation(
    request: IrrigationRequest,
    forecast: Sequence[ForecastDay],
    *,
    source: Literal["user", "open-meteo"],
) -> dict:
    """Apply ET and rain, then refill the entire deficit if the trigger is reached.

    The trigger is not a storage capacity and does not cap the irrigation depth.
    Rain beyond the current deficit drains; no negative deficit is carried ahead.
    Values are deliberately not rounded during the water-balance calculation.
    """
    efficiency = IRRIGATION_EFFICIENCY[request.irrigation_method]
    deficit = request.current_deficit_mm
    plan = []
    for day in forecast:
        opening_deficit = deficit
        crop_et = day.et0_mm * request.kc
        demand = opening_deficit + crop_et
        infiltrating_rain = day.rain_mm * request.effective_rain_fraction
        effective_rain = min(infiltrating_rain, demand)
        drainage = max(0.0, infiltrating_rain - demand)
        deficit = max(0.0, demand - effective_rain)
        before_irrigation = deficit
        irrigation_needed = deficit >= request.allowed_deficit_mm
        net_mm = deficit if irrigation_needed else 0.0
        gross_mm = net_mm / efficiency
        deficit -= net_mm
        plan.append({
            "date": day.date.isoformat(),
            "et0_mm": day.et0_mm,
            "crop_et_mm": crop_et,
            "rain_mm": day.rain_mm,
            "effective_rain_mm": effective_rain,
            "drainage_mm": drainage,
            "excluded_rain_mm": day.rain_mm - infiltrating_rain,
            "opening_deficit_mm": opening_deficit,
            "deficit_before_irrigation_mm": before_irrigation,
            "irrigation_needed": irrigation_needed,
            "net_irrigation_mm": net_mm,
            "gross_irrigation_mm": gross_mm,
            # 1 mm * 1000 m² = 1 m³; one decare is 1000 m².
            "irrigation_volume_m3": gross_mm * request.area_decare,
            "end_deficit_mm": deficit,
        })

    warnings = [
        "Tahmini günlük su dengesi; ölçülmüş su tasarrufu veya sulama talimatı değildir.",
        "Kc, başlangıç açığı ve eşik kullanıcı girdisidir; toprak kapasitesi doğrulanmaz.",
        "Günlük ET ve yağıştan sonra eşik değerlendirilir; gün içi zamanlama modellenmez.",
        "Verim yaklaşık tarla uygulama verimidir; iletim kayıpları modellenmez.",
        "Etkili yağış katsayısı varsayımdır; fazla sızan yağış drenaj olarak ayrılır.",
    ]
    if request.current_deficit_mm >= request.allowed_deficit_mm:
        warnings.append(
            "Başlangıç açığı eşiğe ulaşmış/aşmış: günlük yağış sonrası kalan açığın tamamı değerlendirilir."
        )
    if source == "user":
        warnings.append("Çevrimdışı senaryo: hava satırları kullanıcı tarafından sağlandı, doğrulanmış tahmin değildir.")
    return {
        "source": source,
        "timezone": FORECAST_TIMEZONE,
        "predictions_only": True,
        "auto_action": False,
        "latitude": request.latitude,
        "longitude": request.longitude,
        "area_decare": request.area_decare,
        "kc": request.kc,
        "current_deficit_mm": request.current_deficit_mm,
        "allowed_deficit_mm": request.allowed_deficit_mm,
        "effective_rain_fraction": request.effective_rain_fraction,
        "irrigation_method": request.irrigation_method,
        "irrigation_efficiency": efficiency,
        "total_net_irrigation_mm": sum(day["net_irrigation_mm"] for day in plan),
        "total_gross_irrigation_mm": sum(day["gross_irrigation_mm"] for day in plan),
        "total_irrigation_volume_m3": sum(day["irrigation_volume_m3"] for day in plan),
        "final_deficit_mm": deficit,
        "days": plan,
        "warnings": warnings,
    }
