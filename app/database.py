import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

logger = logging.getLogger(__name__)


def veritabani_url_al() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Eski kurulumlarla uyumluluk: yalnizca `sifre` tanimliysa eski adresi kullan.
    sifre = os.getenv("sifre")
    if sifre is not None:
        logger.warning(
            "`sifre` ortam degiskeni kullanimdan kalkiyor; "
            "bunun yerine DATABASE_URL tanimlayin (bkz. .env.example)."
        )
        return f"mysql+pymysql://root:{sifre}@localhost:3306/tarim_karar_analiz"

    raise RuntimeError(
        "DATABASE_URL tanimli degil. .env.example dosyasini .env olarak kopyalayip doldurun."
    )


SQLALCHEMY_DATABASE_URL = veritabani_url_al()

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
