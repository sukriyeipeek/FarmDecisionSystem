import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

def veritabani_url_al() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    raise RuntimeError(
        "DATABASE_URL tanimli degil; .env.example dosyasini .env olarak kopyalayip doldurun."
    )


SQLALCHEMY_DATABASE_URL = veritabani_url_al()

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
