import pytest

from app import auth


def test_kisa_jwt_secret_reddedilir(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "kisa")
    with pytest.raises(RuntimeError):
        auth.token_olustur(1)


def test_jwt_secret_yoksa_reddedilir(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        auth.token_olustur(1)
