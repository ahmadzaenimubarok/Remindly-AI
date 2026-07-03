import logging

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


async def send_comment_reply(
    page_token: str, comment_id: str, message: str
) -> bool:
    """Balas komentar Facebook via Graph API. Kembalikan True jika berhasil."""
    url = f"{GRAPH_API_BASE}/{comment_id}/comments"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                params={"access_token": page_token},
                json={"message": message},
            )
            response.raise_for_status()
            logger.info("Comment reply sent", extra={"comment_id": comment_id})
            return True
    except Exception:
        logger.exception("send_comment_reply failed", extra={"comment_id": comment_id})
        return False


async def send_messenger_reply(
    page_token: str, recipient_id: str, message: str
) -> bool:
    """Kirim pesan Messenger via Graph API. Kembalikan True jika berhasil."""
    url = f"{GRAPH_API_BASE}/me/messages"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                params={"access_token": page_token},
                json={
                    "recipient": {"id": recipient_id},
                    "message": {"text": message},
                    "messaging_type": "RESPONSE",
                },
            )
            response.raise_for_status()
            logger.info("Messenger reply sent", extra={"recipient_id": recipient_id})
            return True
    except Exception:
        logger.exception("send_messenger_reply failed", extra={"recipient_id": recipient_id})
        return False
