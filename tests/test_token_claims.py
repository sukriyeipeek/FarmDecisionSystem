from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app import auth


@pytest.mark.parametrize('missing', ['exp', 'iat', 'sub'])
def test_required_token_claims(missing):
    now = datetime.now(timezone.utc)
    claims = {'sub': '1', 'iat': now, 'exp': now + timedelta(minutes=1)}
    del claims[missing]
    token = jwt.encode(claims, auth._secret_al(), algorithm=auth.ALGORITHM)
    with pytest.raises(HTTPException) as error:
        auth.token_coz(token)
    assert error.value.status_code == 401


@pytest.mark.parametrize('subject', [None, 1, '-1', '0', '1.5', ''])
def test_invalid_subjects_return_401(subject):
    now = datetime.now(timezone.utc)
    token = jwt.encode({'sub': subject, 'iat': now, 'exp': now + timedelta(minutes=1)}, auth._secret_al(), algorithm=auth.ALGORITHM)
    with pytest.raises(HTTPException) as error:
        auth.token_coz(token)
    assert error.value.status_code == 401


@pytest.mark.parametrize('minutes', ['0', '-1', '1441'])
def test_invalid_session_duration_rejected(monkeypatch, minutes):
    monkeypatch.setenv('JWT_EXPIRE_MINUTES', minutes)
    with pytest.raises(ValueError):
        auth.token_olustur(1)
