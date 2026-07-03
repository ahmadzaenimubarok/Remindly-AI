import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


async def provision_tenant(name: str, email: str, db: AsyncSession) -> Tenant:
    tenant = Tenant(
        name=name,
        email=email,
        plan="free",
        ai_config={
            "tone": "casual",
            "niche": [],
            "posting_hours": [9, 12, 19],
            "intent_threshold": 0.75,
            "auto_approve": False,
        },
    )
    db.add(tenant)
    await db.flush()  # dapatkan ID tanpa commit (commit ada di luar)
    logger.info(
        "Tenant provisioned",
        extra={"tenant_id": str(tenant.id), "email": email},
    )
    return tenant
