"""Authenticated water catalogue and optional forecast-based planning endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import mevcut_kullanici
from app.services.irrigation_service import IrrigationRequest, simulate_irrigation
from app.services.water_service import water_catalog
from app.services.weather_service import WeatherUnavailable, get_forecast

router = APIRouter(tags=["Su ve sulama"], dependencies=[Depends(mevcut_kullanici)])


@router.get("/su/katalog")
def su_katalog():
    return water_catalog()


@router.post("/sulama/oneri")
def sulama_oneri(request: IrrigationRequest):
    if request.forecast is not None:
        forecast = request.forecast
        source = "user"
    else:
        try:
            forecast = get_forecast(request.latitude, request.longitude)
        except WeatherUnavailable as exc:
            raise HTTPException(
                status_code=503,
                detail="Hava tahmini şu anda alınamıyor veya geçersiz; lütfen daha sonra tekrar deneyin.",
            ) from exc
        source = "open-meteo"
    return simulate_irrigation(request, forecast, source=source)
