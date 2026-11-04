import pytest

from app import auth
from app import database


def test_kisa_jwt_secret_reddedilir(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "kisa")
    with pytest.raises(RuntimeError):
        auth.token_olustur(1)


def test_jwt_secret_yoksa_reddedilir(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        auth.token_olustur(1)

def test_database_url_zorunludur(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("sifre", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database.veritabani_url_al()

def test_legacy_sifre_fallback_reddedilir(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("sifre", "legacy")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database.veritabani_url_al()
