import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import FeatureStatus, check_feature_status, log_skip
from app.core.security import decrypt_credential
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.session import Session
from app.models.system_log import SystemLog
from app.models.tenant import Tenant
from app.models.tenant_credential import TenantCredential
from app.services.facebook_service import get_messenger_user_name, send_comment_reply, send_messenger_reply
from app.services.instagram_service import get_instagram_user_name, send_instagram_dm
from app.services.openai_service import IntentResult, check_continuation, classify_intent, generate_reply
from app.services.rag_service import get_product_context

logger = logging.getLogger(__name__)

FAREWELL_KEYWORDS: frozenset[str] = frozenset({
    "terima kasih", "terimakasih", "makasih", "trims",
    "sampai jumpa", "dadah", "selesai", "oke deh", "oke thanks",
    "ok thanks", "thanks", "thank you", "bye", "goodbye", "done",
})

FAREWELL_INTENTS: frozenset[str] = frozenset({"spam"})


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


async def _get_instagram_credential(
    tenant_id: str, db: AsyncSession
) -> TenantCredential | None:
    result = await db.execute(
        select(TenantCredential).where(
            TenantCredential.tenant_id == uuid.UUID(tenant_id),
            TenantCredential.platform == "instagram",
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
    elif name and not customer.name:
        customer.name = name
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


def _is_closing_signal(
    message_in: str | None,
    message_out: str | None,
    intent: str | None,
) -> bool:
    """True jika percakapan ini menandakan sesi selesai."""
    if intent in FAREWELL_INTENTS:
        return True
    for text in (message_in, message_out):
        if text and any(kw in text.lower() for kw in FAREWELL_KEYWORDS):
            return True
    return False


async def _get_open_session(
    tenant_id: str,
    customer_id: uuid.UUID,
    platform: str,
    channel_type: str,
    db: AsyncSession,
) -> Session | None:
    result = await db.execute(
        select(Session).where(
            Session.tenant_id == uuid.UUID(tenant_id),
            Session.customer_id == customer_id,
            Session.platform == platform,
            Session.channel_type == channel_type,
            Session.status == "open",
        )
    )
    return result.scalar_one_or_none()


async def _get_last_closed_session_messages(
    tenant_id: str,
    customer_id: uuid.UUID,
    platform: str,
    channel_type: str,
    db: AsyncSession,
) -> tuple[Session | None, list[str]]:
    sess_result = await db.execute(
        select(Session).where(
            Session.tenant_id == uuid.UUID(tenant_id),
            Session.customer_id == customer_id,
            Session.platform == platform,
            Session.channel_type == channel_type,
            Session.status == "closed",
        ).order_by(Session.closed_at.desc()).limit(1)
    )
    last_session = sess_result.scalar_one_or_none()
    if last_session is None:
        return None, []

    msg_result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == uuid.UUID(tenant_id),
            Conversation.session_id == last_session.id,
            Conversation.message_in.isnot(None),
        ).order_by(Conversation.created_at.desc()).limit(5)
    )
    msgs = msg_result.scalars().all()
    return last_session, [m.message_in for m in reversed(msgs) if m.message_in]


async def _get_or_create_session(
    tenant_id: str,
    customer_id: uuid.UUID,
    platform: str,
    channel_type: str,
    message_in: str,
    db: AsyncSession,
) -> tuple[Session, list[str]]:
    """
    Cari sesi yang masih open, atau buat sesi baru.
    Kalau semua sesi closed, cek apakah pesan baru adalah lanjutan sesi sebelumnya.
    Return (session, prior_messages_for_context).
    """
    open_session = await _get_open_session(tenant_id, customer_id, platform, channel_type, db)
    if open_session is not None:
        return open_session, []

    last_session, prior_texts = await _get_last_closed_session_messages(
        tenant_id, customer_id, platform, channel_type, db
    )

    is_continuation = False
    prior_session_id = None
    if last_session is not None and prior_texts:
        is_continuation = await check_continuation(message_in, prior_texts)
        if is_continuation:
            prior_session_id = last_session.id
            logger.info(
                "Continuation detected",
                extra={"tenant_id": tenant_id, "customer_id": str(customer_id),
                       "prior_session_id": str(prior_session_id)},
            )

    new_session = Session(
        tenant_id=uuid.UUID(tenant_id),
        customer_id=customer_id,
        platform=platform,
        channel_type=channel_type,
        status="open",
        is_continuation=is_continuation,
        prior_session_id=prior_session_id,
    )
    db.add(new_session)
    await db.flush()
    return new_session, (prior_texts if is_continuation else [])


async def process_facebook_comment(
    tenant_id: str, event: dict, db: AsyncSession
) -> str | None:
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
        return None

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        logger.error("Tenant not found", extra={"tenant_id": tenant_id})
        return None

    credential = await _get_facebook_credential(tenant_id, db)
    if credential is None or credential.is_expired():
        await _save_system_log(
            tenant_id, "comment_reply", "skipped",
            {"reason": "no_credential", "comment_id": comment_id}, db,
        )
        return None

    # Dedup: skip jika sudah pernah diproses
    existing = await _get_conversation_by_platform_id(tenant_id, comment_id, db)
    if existing is not None:
        if existing.is_human_takeover:
            logger.info("Skipping — human takeover active", extra={"comment_id": comment_id})
        return None

    customer = await _get_or_create_customer(tenant_id, from_id, "facebook", from_name, db)
    session, prior_context_msgs = await _get_or_create_session(
        tenant_id, customer.id, "facebook", "comment", message, db
    )
    prior_context_str = "\n".join(prior_context_msgs) if prior_context_msgs else None

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
            session_id=session.id,
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
        return str(customer.id)

    tone = tenant.ai_config.get("tone", "casual")
    reply = await generate_reply(message, product_context, tone, prior_context=prior_context_str)
    sent = await send_comment_reply(page_token, comment_id, reply)

    conv = Conversation(
        tenant_id=uuid.UUID(tenant_id),
        customer_id=customer.id,
        session_id=session.id,
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

    if _is_closing_signal(message, reply if sent else None, intent_result.intent):
        session.status = "closed"
        session.closed_at = datetime.now(timezone.utc)
        logger.info("Session closed by AI signal", extra={"session_id": str(session.id)})

    await _save_system_log(
        tenant_id, "comment_reply", "success" if sent else "failed",
        {"comment_id": comment_id, "sent": sent}, db,
    )
    return str(customer.id)


async def process_messenger_message(
    tenant_id: str, event: dict, db: AsyncSession
) -> str | None:
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
        return None

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        return None

    credential = await _get_facebook_credential(tenant_id, db)
    if credential is None or credential.is_expired():
        await _save_system_log(
            tenant_id, "messenger_reply", "skipped",
            {"reason": "no_credential", "message_id": message_id}, db,
        )
        return None

    existing = await _get_conversation_by_platform_id(tenant_id, message_id, db)
    if existing is not None:
        return None

    page_token = decrypt_credential(credential.access_token_encrypted)
    sender_name = await get_messenger_user_name(page_token, sender_id)
    customer = await _get_or_create_customer(tenant_id, sender_id, "messenger", sender_name, db)

    session, prior_context_msgs = await _get_or_create_session(
        tenant_id, customer.id, "messenger", "dm", message, db
    )
    prior_context_str = "\n".join(prior_context_msgs) if prior_context_msgs else None

    product_context = await get_product_context(tenant_id, message, db)
    tenant_context = f"Nama toko: {tenant.name}\n{product_context}"

    intent_result = await classify_intent(message, tenant_context)

    escalation_topics: list[str] = tenant.ai_config.get("escalation_topics", [])
    should_escalate, escalation_reason = _should_escalate(message, intent_result, escalation_topics)

    if should_escalate:
        conv = Conversation(
            tenant_id=uuid.UUID(tenant_id),
            customer_id=customer.id,
            session_id=session.id,
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
        return str(customer.id)

    tone = tenant.ai_config.get("tone", "casual")
    reply = await generate_reply(message, product_context, tone, prior_context=prior_context_str)
    sent = await send_messenger_reply(page_token, sender_id, reply)

    conv = Conversation(
        tenant_id=uuid.UUID(tenant_id),
        customer_id=customer.id,
        session_id=session.id,
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

    if _is_closing_signal(message, reply if sent else None, intent_result.intent):
        session.status = "closed"
        session.closed_at = datetime.now(timezone.utc)
        logger.info("Session closed by AI signal", extra={"session_id": str(session.id)})

    await _save_system_log(
        tenant_id, "messenger_reply", "success" if sent else "failed",
        {"message_id": message_id, "sent": sent}, db,
    )
    return str(customer.id)


async def process_instagram_dm(
    tenant_id: str, event: dict, db: AsyncSession
) -> str | None:
    """
    Proses event Instagram DM untuk satu tenant.
    event keys: message_id, message, sender_id
    """
    message_id: str = event["message_id"]
    message: str = event["message"]
    sender_id: str = event["sender_id"]

    status = await check_feature_status(tenant_id, "instagram_reply", db)
    if status != FeatureStatus.ACTIVE:
        await log_skip(tenant_id, "instagram_reply", status)
        return None

    tenant = await _get_tenant(tenant_id, db)
    if tenant is None:
        logger.error("Tenant not found", extra={"tenant_id": tenant_id})
        return None

    credential = await _get_instagram_credential(tenant_id, db)
    if credential is None or credential.is_expired():
        await _save_system_log(
            tenant_id, "instagram_dm_reply", "skipped",
            {"reason": "no_credential", "message_id": message_id}, db,
        )
        return None

    existing = await _get_conversation_by_platform_id(tenant_id, message_id, db)
    if existing is not None:
        return None

    page_token = decrypt_credential(credential.access_token_encrypted)
    sender_name = await get_instagram_user_name(page_token, sender_id)
    customer = await _get_or_create_customer(tenant_id, sender_id, "instagram", sender_name, db)

    session, prior_context_msgs = await _get_or_create_session(
        tenant_id, customer.id, "instagram", "dm", message, db
    )
    prior_context_str = "\n".join(prior_context_msgs) if prior_context_msgs else None

    product_context = await get_product_context(tenant_id, message, db)
    tenant_context = f"Nama toko: {tenant.name}\n{product_context}"

    intent_result = await classify_intent(message, tenant_context)

    escalation_topics: list[str] = tenant.ai_config.get("escalation_topics", [])
    should_escalate, escalation_reason = _should_escalate(message, intent_result, escalation_topics)

    if should_escalate:
        conv = Conversation(
            tenant_id=uuid.UUID(tenant_id),
            customer_id=customer.id,
            session_id=session.id,
            platform="instagram",
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
            tenant_id, "instagram_dm_escalated", "success",
            {"message_id": message_id, "reason": escalation_reason}, db,
        )
        return str(customer.id)

    tone = tenant.ai_config.get("tone", "casual")
    reply = await generate_reply(message, product_context, tone, prior_context=prior_context_str)
    sent = await send_instagram_dm(page_token, sender_id, reply)

    conv = Conversation(
        tenant_id=uuid.UUID(tenant_id),
        customer_id=customer.id,
        session_id=session.id,
        platform="instagram",
        channel_type="dm",
        platform_message_id=message_id,
        message_in=message,
        message_out=reply if sent else None,
        intent=intent_result.intent,
        sentiment=intent_result.sentiment,
        is_human_takeover=False,
    )
    db.add(conv)

    if _is_closing_signal(message, reply if sent else None, intent_result.intent):
        session.status = "closed"
        session.closed_at = datetime.now(timezone.utc)
        logger.info("Session closed by AI signal", extra={"session_id": str(session.id)})

    await _save_system_log(
        tenant_id, "instagram_dm_reply", "success" if sent else "failed",
        {"message_id": message_id, "sent": sent}, db,
    )
    return str(customer.id)
