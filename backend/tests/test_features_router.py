from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db_session
from app.core.feature_flags import FeatureStatus
from app.core.security import create_access_token
from app.main import app
import uuid


def _mock_db():
    yield MagicMock()


@pytest.fixture
def client_with_mock_db():
    app.dependency_overrides[get_db_session] = _mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_db_session, None)


def _auth_cookie(client):
    token = create_access_token({
        "sub": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "role": "tenant_user",
    })
    client.cookies.set("access_token", token)


def test_feature_endpoint_requires_auth(client):
    res = client.get("/api/v1/features/facebook_engagement")
    assert res.status_code == 401


def test_known_feature_returns_status(client_with_mock_db):
    _auth_cookie(client_with_mock_db)
    with patch("app.routers.features.check_feature_status", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = FeatureStatus.ACTIVE
        res = client_with_mock_db.get("/api/v1/features/facebook_engagement")
    client_with_mock_db.cookies.clear()
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "active"


def test_not_configured_feature_returns_not_configured(client_with_mock_db):
    _auth_cookie(client_with_mock_db)
    with patch("app.routers.features.check_feature_status", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = FeatureStatus.NOT_CONFIGURED
        res = client_with_mock_db.get("/api/v1/features/unknown_feature_xyz")
    client_with_mock_db.cookies.clear()
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "not_configured"


def test_plan_locked_feature_returns_plan_locked(client_with_mock_db):
    _auth_cookie(client_with_mock_db)
    with patch("app.routers.features.check_feature_status", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = FeatureStatus.PLAN_LOCKED
        res = client_with_mock_db.get("/api/v1/features/premium_feature")
    client_with_mock_db.cookies.clear()
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "plan_locked"
