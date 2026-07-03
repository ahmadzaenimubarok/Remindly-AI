import uuid

import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.base import APIError, APIResponse
from app.schemas.tenant import TenantResponse


def test_api_response_generic():
    res = APIResponse[dict](success=True, data={"key": "val"})
    assert res.success is True
    assert res.data["key"] == "val"


def test_api_error_has_code():
    err = APIError(message="Terjadi kesalahan", code="INTERNAL_ERROR")
    assert err.success is False
    assert err.code == "INTERNAL_ERROR"


def test_register_request_validates_email():
    with pytest.raises(ValidationError):
        RegisterRequest(name="Test", email="bukan-email", password="secret123")


def test_register_request_validates_password_min_length():
    with pytest.raises(ValidationError):
        RegisterRequest(name="Test", email="test@test.com", password="short")


def test_login_request_valid():
    req = LoginRequest(email="user@example.com", password="anypass")
    assert req.email == "user@example.com"


def test_tenant_response_from_attributes():
    tenant_id = uuid.uuid4()
    res = TenantResponse(id=tenant_id, name="Toko Kece", email="toko@test.com", plan="free")
    assert res.plan == "free"
