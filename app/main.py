import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.routes
from app.auth import _secret_al, _sure_dakika
from app.water_routes import router as water_router

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    _secret_al()
    if _sure_dakika() <= 0:
        raise RuntimeError("JWT_EXPIRE_MINUTES pozitif olmalıdır.")
    yield

app_tarim = FastAPI(
    title="Tarımsal Karar ve Risk Analiz Sistemi",
    description="Çiftçiler için risk analizi ve arazi optimizasyonu sağlayan backend servisi.",
    version="1.0.0",
    lifespan=lifespan,
)

@app_tarim.get("/")
def baslangic():
    return {
        "mesaj": "Backend API sorunsuz çalışıyor!",
        "proje": "Yapay Zeka Destekli Tarımsal Karar ve Risk Analiz Sistemi",
        "durum": "Aktif",
    }

@app_tarim.get("/health")
def health():
    return {"status": "ok"}

VARSAYILAN_ORIGINS = "http://localhost:5173,http://localhost:5174"
origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", VARSAYILAN_ORIGINS).split(",")
    if o.strip()
]

app_tarim.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app_tarim.include_router(app.routes.router)
app_tarim.include_router(water_router)
