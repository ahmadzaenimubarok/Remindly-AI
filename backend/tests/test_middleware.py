import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.middleware.error_handler import global_exception_handler
from app.middleware.tenant_context import TenantContextMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)
    app.add_exception_handler(Exception, global_exception_handler)

    @app.get("/api/v1/protected")
    async def protected(request: Request):
        return {
            "success": True,
            "data": {
                "tenant_id": str(request.state.tenant_id),
                "role": request.state.role,
            },
        }

    @app.get("/api/v1/crash")
    async def crash():
        raise RuntimeError("intentional crash")

    return app


from fastapi import Request


@pytest.fixture
def client():
    return TestClient(_make_app(), raise_server_exceptions=False)


def test_protected_without_token_returns_401(client):
    res = client.get("/api/v1/protected")
    assert res.status_code == 401
    assert res.json()["success"] is False
    assert res.json()["code"] == "UNAUTHORIZED"


def test_protected_with_valid_token_returns_200(client):
    token = create_access_token(
        {"sub": "user-123", "tenant_id": "tenant-abc", "role": "tenant_user"}
    )
    res = client.get("/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["data"]["tenant_id"] == "tenant-abc"


def test_protected_with_invalid_token_returns_401(client):
    res = client.get("/api/v1/protected", headers={"Authorization": "Bearer bad.token"})
    assert res.status_code == 401


def test_exception_handler_returns_clean_error(client):
    token = create_access_token({"sub": "u", "tenant_id": "t", "role": "tenant_user"})
    res = client.get("/api/v1/crash", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 500
    assert res.json()["success"] is False
    assert res.json()["code"] == "INTERNAL_ERROR"
    assert "Traceback" not in res.text
    assert "RuntimeError" not in res.text
