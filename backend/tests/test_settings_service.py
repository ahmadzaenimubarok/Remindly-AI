import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.settings_service import get_settings_status, save_fb_token


def _mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_get_settings_status_no_credential():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    cred_result = MagicMock()
    cred_result.scalar_one_or_none.return_value = None

    count_result = MagicMock()
    count_result.scalar.return_value = 0

    db.execute.side_effect = [cred_result, count_result]

    status = await get_settings_status(tenant_id, db)
    assert status["facebook_connected"] is False
    assert status["product_count"] == 0


@pytest.mark.asyncio
async def test_get_settings_status_with_credential():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    cred = MagicMock()
    cred.is_expired.return_value = False
    cred_result = MagicMock()
    cred_result.scalar_one_or_none.return_value = cred

    count_result = MagicMock()
    count_result.scalar.return_value = 3

    db.execute.side_effect = [cred_result, count_result]

    status = await get_settings_status(tenant_id, db)
    assert status["facebook_connected"] is True
    assert status["product_count"] == 3


@pytest.mark.asyncio
async def test_save_fb_token_creates_new():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None
    db.execute.return_value = existing_result

    with patch("app.services.settings_service.encrypt_credential", return_value="encrypted_token"):
        result = await save_fb_token(tenant_id, "raw_token_123", "page_id_456", db)

    db.add.assert_called_once()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_save_fb_token_updates_existing():
    tenant_id = str(uuid.uuid4())
    db = _mock_db()

    existing_cred = MagicMock()
    existing_cred.access_token_encrypted = "old_encrypted"
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = existing_cred
    db.execute.return_value = existing_result

    with patch("app.services.settings_service.encrypt_credential", return_value="new_encrypted"):
        result = await save_fb_token(tenant_id, "new_token", "page_id_456", db)

    assert result.access_token_encrypted == "new_encrypted"
    db.add.assert_not_called()
