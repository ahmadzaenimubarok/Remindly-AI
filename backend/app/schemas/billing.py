from pydantic import BaseModel, Field


class CreateCheckoutSessionRequest(BaseModel):
    plan: str = Field(..., pattern="^(starter|pro|enterprise)$")
    success_url: str = Field(..., min_length=10)
    cancel_url: str = Field(..., min_length=10)


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    modified: bool = False


class BillingStatusResponse(BaseModel):
    plan: str
    plan_expires_at: str | None
    stripe_customer_id: str | None
    pending_plan: str | None
    pending_plan_date: str | None
