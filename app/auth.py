import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal

ALGORITHM = "HS256"
MIN_SECRET_LENGTH = 32

# auto_error=False: eksik basligi kendimiz 401 olarak donduruyoruz
bearer_semasi = HTTPBearer(auto_error=False)


def _secret_al() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"JWT_SECRET tanimli degil veya {MIN_SECRET_LENGTH} karakterden kisa (bkz. .env.example)."
        )
    return secret


def _sure_dakika() -> int:
    return int(os.getenv("JWT_EXPIRE_MINUTES", "480"))


def token_olustur(kullanici_id: int) -> str:
    simdi = datetime.now(timezone.utc)
    payload = {
        "sub": str(kullanici_id),
        "iat": simdi,
        "exp": simdi + timedelta(minutes=_sure_dakika()),
    }
    return jwt.encode(payload, _secret_al(), algorithm=ALGORITHM)


def token_coz(token: str) -> int:
    try:
        payload = jwt.decode(token, _secret_al(), algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum geçersiz veya süresi dolmuş. Lütfen tekrar giriş yapın.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def mevcut_kullanici(
    kimlik: HTTPAuthorizationCredentials | None = Depends(bearer_semasi),
    db: Session = Depends(get_db),
) -> models.Kullanici:
    if kimlik is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Giriş yapmanız gerekiyor.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    kullanici_id = token_coz(kimlik.credentials)
    kullanici = (
        db.query(models.Kullanici)
        .filter(models.Kullanici.kullanici_id == kullanici_id)
        .first()
    )
    if kullanici is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return kullanici


def admin_gerekli(kullanici: models.Kullanici = Depends(mevcut_kullanici)) -> models.Kullanici:
    if not kullanici.is_admin:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkin yok.")
    return kullanici
