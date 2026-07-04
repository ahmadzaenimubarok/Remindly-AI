import logging
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.session import Session
from app.schemas.base import APIResponse
from app.schemas.conversation import ConversationResponse, TakeoverRequest, ThreadMessage, ThreadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("", response_model=APIResponse[list[ConversationResponse]])
async def list_conversations(
    request: Request,
    is_human_takeover: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id

    stmt = (
        select(Conversation)
        .where(Conversation.tenant_id == uuid.UUID(tenant_id))
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    if is_human_takeover is not None:
        stmt = stmt.where(Conversation.is_human_takeover == is_human_takeover)

    result = await db.execute(stmt)
    conversations = result.scalars().all()

    return APIResponse(data=[ConversationResponse.model_validate(c) for c in conversations])


@router.get("/threads", response_model=APIResponse[list[ThreadResponse]])
async def list_threads(
    request: Request,
    is_human_takeover: bool | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    """Return one thread entry per session. Customer dapat muncul >1x jika punya beberapa sesi."""
    tenant_id: str = request.state.tenant_id
    tid = uuid.UUID(tenant_id)

    sess_stmt = (
        select(Session)
        .where(Session.tenant_id == tid)
        .order_by(Session.created_at.desc())
        .limit(limit)
    )
    if status in ("open", "closed"):
        sess_stmt = sess_stmt.where(Session.status == status)

    sess_result = await db.execute(sess_stmt)
    sessions: list[Session] = list(sess_result.scalars().all())

    if not sessions:
        return APIResponse(data=[])

    session_ids = [s.id for s in sessions]

    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == tid,
            Conversation.session_id.in_(session_ids),
        ).order_by(Conversation.created_at.asc())
    )
    all_convs = conv_result.scalars().all()

    convs_by_session: dict[uuid.UUID, list[Conversation]] = defaultdict(list)
    for c in all_convs:
        if c.session_id:
            convs_by_session[c.session_id].append(c)

    if is_human_takeover is not None:
        sessions = [
            s for s in sessions
            if any(m.is_human_takeover for m in convs_by_session.get(s.id, [])) == is_human_takeover
        ]

    customer_ids = list({s.customer_id for s in sessions})
    prior_session_ids = [s.prior_session_id for s in sessions if s.prior_session_id]

    customers: dict[uuid.UUID, Customer] = {}
    if customer_ids:
        cust_result = await db.execute(
            select(Customer).where(
                Customer.tenant_id == tid,
                Customer.id.in_(customer_ids),
            )
        )
        for c in cust_result.scalars().all():
            customers[c.id] = c

    prior_sessions: dict[uuid.UUID, Session] = {}
    if prior_session_ids:
        prior_result = await db.execute(
            select(Session).where(
                Session.tenant_id == tid,
                Session.id.in_(prior_session_ids),
            )
        )
        for ps in prior_result.scalars().all():
            prior_sessions[ps.id] = ps

    threads: list[ThreadResponse] = []
    for sess in sessions:
        msgs = convs_by_session.get(sess.id, [])
        cust = customers.get(sess.customer_id)
        prior_sess = prior_sessions.get(sess.prior_session_id) if sess.prior_session_id else None
        last_msg = msgs[-1] if msgs else None

        threads.append(ThreadResponse(
            session_id=sess.id,
            customer_id=sess.customer_id,
            customer_name=cust.name if cust else None,
            platform=sess.platform,
            channel_type=sess.channel_type,
            status=sess.status,
            is_continuation=sess.is_continuation,
            prior_session_id=sess.prior_session_id,
            prior_session_date=prior_sess.closed_at if prior_sess else None,
            message_count=len(msgs),
            has_human_takeover=any(m.is_human_takeover for m in msgs),
            last_message_at=last_msg.created_at if last_msg else sess.created_at,
            messages=[ThreadMessage.model_validate(m) for m in msgs],
        ))

    threads.sort(key=lambda t: t.last_message_at, reverse=True)
    return APIResponse(data=threads)


@router.patch("/{conversation_id}/takeover", response_model=APIResponse[ConversationResponse])
async def toggle_takeover(
    conversation_id: uuid.UUID,
    body: TakeoverRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id: str = request.state.tenant_id

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == uuid.UUID(tenant_id),  # RULE-03
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation tidak ditemukan.")

    conv.is_human_takeover = body.is_human_takeover
    if not body.is_human_takeover:
        conv.escalation_reason = None

    logger.info(
        "Takeover toggled",
        extra={
            "tenant_id": tenant_id,
            "conversation_id": str(conversation_id),
            "is_human_takeover": body.is_human_takeover,
        },
    )
    return APIResponse(data=ConversationResponse.model_validate(conv))
