import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.database import engine
import app.routes

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

models.Base.metadata.create_all(bind=engine)

app_tarim = FastAPI(
    title="Tarımsal Karar ve Risk Analiz Sistemi",
    description="Çiftçiler için risk analizi ve arazi optimizasyonu sağlayan backend servisi.",
    version="1.0.0",
)

@app_tarim.get("/")
def baslangic():
    return {
        "mesaj": "Backend API sorunsuz çalışıyor!",
        "proje": "Yapay Zeka Destekli Tarımsal Karar ve Risk Analiz Sistemi",
        "durum": "Aktif",
    }

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