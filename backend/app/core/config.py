from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_ENV: str = "development"
    APP_SECRET_KEY: str

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # AI Provider (OpenRouter untuk dev, OpenAI untuk prod)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL_FAST: str = "meta-llama/llama-3.1-8b-instruct:free"
    AI_MODEL_QUALITY: str = "meta-llama/llama-3.1-8b-instruct:free"

    # Meta (Facebook / Messenger)
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_VERIFY_TOKEN: str = ""
    META_REDIRECT_URI: str = ""  # Backend callback URL, e.g. http://localhost:8000/api/v1/auth/facebook/callback
    META_IG_REDIRECT_URI: str = ""  # Backend callback URL untuk Instagram OAuth
    FRONTEND_URL: str = "http://localhost:3000"

    # TikTok
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""

    # WhatsApp
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    # Midtrans
    MIDTRANS_SERVER_KEY: str = ""
    MIDTRANS_CLIENT_KEY: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Email
    RESEND_API_KEY: str = ""

    # Encryption
    CREDENTIAL_ENCRYPTION_KEY: str = ""

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
