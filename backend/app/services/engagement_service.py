import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import FeatureStatus, check_feature_status, log_skip
from app.core.security import decrypt_credential
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.system_log import SystemLog
from app.models.tenant import Tenant
from app.models.tenant_credential import TenantCredential
from app.services.facebook_service import send_comment_reply, send_messenger_reply
from app.services.openai_service import IntentResult, classify_intent, generate_reply
from app.services.rag_service import get_product_context

logger = logging.getLogger(__name__)


async def _get_tenant(tenant_id: str, db: AsyncSession) -> Tenant | None:
    result = await db.execute(
        select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
    )
    return result.scalar_one_or_none()


async def _get_facebook_credential(
    tenant_id: str, db: AsyncSession
) -> TenantCredential | None:
    result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "facebook",
        )
    )
    return result.scalar_one_or_none()


async def _get_or_create_customer(
    tenant_id: str,
    platform_user_id: str,
    platform: str,
    name: str | None,
    db: AsyncSession,
) -> Customer:
    result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == uuid.UUID(tenant_id),
            Customer.platform_user_id == platform_user_id,
            Customer.platform == platform,
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = Customer(
            tenant_id=uuid.UUID(tenant_id),
            platform_user_id=platform_user_id,
            platform=platform,
            name=name,
        )
        db.add(customer)
        await db.flush()
    return customer


async def _get_conversation_by_platform_id(
    tenant_id: str, platform_message_id: str, db: AsyncSession
) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == uuid.UUID(tenant_id),
            Conversation.platform_message_id == platform_message_id,
        )
    )
    return result.scalar_one_or_none()


def _should_escalate(
    message: str, intent_result: IntentResult, escalation_topics: list[str]
) -> tuple[bool, str]:
    """Kembalikan (should_escalate, reason)."""
    msg_lower = message.lower()
    for topic in escalation_topics:
        if topic.lower() in msg_lower:
            return True, f"blacklist_topic:{topic}"
    if intent_result.intent == "komplain" and intent_result.sentiment == "negative":
        return True, "negative_complaint"
    return False, ""


async def _save_system_log(
    tenant_id: str,
    action: str,
    status: str,
    context: dict,
    db: AsyncSession,
) -> None:
    log = SystemLog(
        tenant_id=uuid.UUID(tenant_id),
        engine="engagement_engine",
        action=action,
        status=status,
        context=context,
    )
    db.add(log)


async def process_facebook_comment(
    tenant_id: str, event: dict, db: AsyncSession
) -> None:
    """
    Proses event komentar Facebook untuk satu tenant.
    event keys: comment_id, message, from_id, from_name, post_id
    """
    comment_id: str = event["comment_id"]
    message: str = event["message"]
    from_id: str = event["from_id"]
    from_name: str | None = event.get("from_name")

    # RULE-01: cek feature flag
    status = await check_feature_status(tenant_id, "facebook_reply", db)
    if status != FeatureStatus.ACTIVE:
        await log_skip(tenant_id, "facebook_reply", status)
        return

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        logger.error("Tenant not found", extra={"tenant_id": tenant_id})
        return

    credential = await _get_facebook_credential(tenant_id, db)
    if credential is None or credential.is_expired():
        await _save_system_log(
            tenant_id, "comment_reply", "skipped",
            {"reason": "no_credential", "comment_id": comment_id}, db,
        )
        return

    # Dedup: skip jika sudah pernah diproses
    existing = await _get_conversation_by_platform_id(tenant_id, comment_id, db)
    if existing is not None:
        if existing.is_human_takeover:
            logger.info("Skipping — human takeover active", extra={"comment_id": comment_id})
        return

    customer = await _get_or_create_customer(tenant_id, from_id, "facebook", from_name, db)

    # RAG context
    product_context = await get_product_context(tenant_id, message, db)
    tenant_context = f"Nama toko: {tenant.name}\n{product_context}"

    # Classify intent
    intent_result = await classify_intent(message, tenant_context)

    escalation_topics: list[str] = tenant.ai_config.get("escalation_topics", [])
    should_escalate, escalation_reason = _should_escalate(message, intent_result, escalation_topics)

    page_token = decrypt_credential(credential.access_token_encrypted)

    if should_escalate:
        conv = Conversation(
            tenant_id=uuid.UUID(tenant_id),
            customer_id=customer.id,
            platform="facebook",
            channel_type="comment",
            platform_message_id=comment_id,
            message_in=message,
            message_out=None,
            intent=intent_result.intent,
            sentiment=intent_result.sentiment,
            is_human_takeover=True,
            escalation_reason=escalation_reason,
        )
        db.add(conv)
        await _save_system_log(
            tenant_id, "comment_escalated", "success",
            {"comment_id": comment_id, "reason": escalation_reason}, db,
        )
        logger.info(
            "Conversation escalated to human",
            extra={"tenant_id": tenant_id, "reason": escalation_reason},
        )
        return

    tone = tenant.ai_config.get("tone", "casual")
    reply = await generate_reply(message, product_context, tone)
    sent = await send_comment_reply(page_token, comment_id, reply)

    conv = Conversation(
        tenant_id=uuid.UUID(tenant_id),
        customer_id=customer.id,
        platform="facebook",
        channel_type="comment",
        platform_message_id=comment_id,
        message_in=message,
        message_out=reply if sent else None,
        intent=intent_result.intent,
        sentiment=intent_result.sentiment,
        is_human_takeover=False,
    )
    db.add(conv)

    await _save_system_log(
        tenant_id, "comment_reply", "success" if sent else "failed",
        {"comment_id": comment_id, "sent": sent}, db,
    )


async def process_messenger_message(
    tenant_id: str, event: dict, db: AsyncSession
) -> None:
    """
    Proses event Messenger DM untuk satu tenant.
    event keys: message_id, message, sender_id
    """
    message_id: str = event["message_id"]
    message: str = event["message"]
    sender_id: str = event["sender_id"]

    status = await check_feature_status(tenant_id, "facebook_reply", db)
    if status != FeatureStatus.ACTIVE:
        await log_skip(tenant_id, "facebook_reply", status)
        return

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        return

    credential = await _get_facebook_credential(tenant_id, db)
    if credential is None or credential.is_expired():
        await _save_system_log(
            tenant_id, "messenger_reply", "skipped",
            {"reason": "no_credential", "message_id": message_id}, db,
        )
        return

    existing = await _get_conversation_by_platform_id(tenant_id, message_id, db)
    if existing is not None:
        if existing.is_human_takeover:
            return
        return

    customer = await _get_or_create_customer(tenant_id, sender_id, "messenger", None, db)

    product_context = await get_product_context(tenant_id, message, db)
    tenant_context = f"Nama toko: {tenant.name}\n{product_context}"

    intent_result = await classify_intent(message, tenant_context)

    escalation_topics: list[str] = tenant.ai_config.get("escalation_topics", [])
    should_escalate, escalation_reason = _should_escalate(message, intent_result, escalation_topics)

    page_token = decrypt_credential(credential.access_token_encrypted)

    if should_escalate:
        conv = Conversation(
            tenant_id=uuid.UUID(tenant_id),
            customer_id=customer.id,
            platform="messenger",
            channel_type="dm",
            platform_message_id=message_id,
            message_in=message,
            message_out=None,
            intent=intent_result.intent,
            sentiment=intent_result.sentiment,
            is_human_takeover=True,
            escalation_reason=escalation_reason,
        )
        db.add(conv)
        await _save_system_log(
            tenant_id, "messenger_escalated", "success",
            {"message_id": message_id, "reason": escalation_reason}, db,
        )
        return

    tone = tenant.ai_config.get("tone", "casual")
    reply = await generate_reply(message, product_context, tone)
    sent = await send_messenger_reply(page_token, sender_id, reply)

    conv = Conversation(
        tenant_id=uuid.UUID(tenant_id),
        customer_id=customer.id,
        platform="messenger",
        channel_type="dm",
        platform_message_id=message_id,
        message_in=message,
        message_out=reply if sent else None,
        intent=intent_result.intent,
        sentiment=intent_result.sentiment,
        is_human_takeover=False,
    )
    db.add(conv)

    await _save_system_log(
        tenant_id, "messenger_reply", "success" if sent else "failed",
        {"message_id": message_id, "sent": sent}, db,
    )
