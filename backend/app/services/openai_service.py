import json
import logging
from dataclasses import dataclass

import openai

from app.core.config import get_settings

logger = logging.getLogger(__name__)

FALLBACK_REPLY = "Halo! Terima kasih sudah menghubungi kami. Tim kami akan segera membalas pesanmu ya 🙏"

INTENT_SYSTEM_PROMPT = """Kamu adalah classifier intent untuk customer service toko online Indonesia.
Klasifikasikan pesan customer ke salah satu intent berikut:
- tanya_info: pertanyaan tentang produk, harga, stok, pengiriman
- niat_beli: menunjukkan minat beli, mau order, tanya cara beli
- komplain: keluhan, ketidakpuasan, masalah pesanan
- spam: pesan tidak relevan, promosi, atau tidak bermakna

Kembalikan HANYA JSON valid dengan format:
{"intent": "<salah satu dari 4 intent>", "sentiment": "<positive|neutral|negative>", "confidence": <0.0-1.0>}"""

REPLY_SYSTEM_PROMPT = """Kamu adalah asisten customer service toko online Indonesia yang ramah dan helpful.
Balas pesan customer dengan gaya bahasa: {tone}.
Gunakan HANYA informasi dari konteks produk yang diberikan — jangan membuat klaim yang tidak ada di konteks.
Jika informasi tidak tersedia di konteks, katakan kamu akan cek dulu.
Balas dalam bahasa Indonesia yang natural, singkat (maks 3 kalimat), dan tidak berlebihan."""


@dataclass
class IntentResult:
    intent: str
    sentiment: str
    confidence: float


def get_llm_client() -> openai.AsyncOpenAI:
    settings = get_settings()
    if settings.OPENROUTER_API_KEY:
        return openai.AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )
    return openai.AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )


async def classify_intent(message: str, tenant_context: str) -> IntentResult:
    settings = get_settings()
    client = get_llm_client()
    raw = ""
    try:
        response = await client.chat.completions.create(
            model=settings.AI_MODEL_FAST,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Konteks toko: {tenant_context}\n\nPesan customer: {message}",
                },
            ],
            temperature=0.1,
            max_tokens=100,
        )
        raw = response.choices[0].message.content or ""
        data = json.loads(raw.strip())
        return IntentResult(
            intent=data.get("intent", "tanya_info"),
            sentiment=data.get("sentiment", "neutral"),
            confidence=float(data.get("confidence", 0.5)),
        )
    except json.JSONDecodeError:
        logger.warning("classify_intent: JSON parse gagal", extra={"raw": raw[:200]})
        return IntentResult(intent="tanya_info", sentiment="neutral", confidence=0.0)
    except Exception:
        logger.exception("classify_intent error")
        return IntentResult(intent="tanya_info", sentiment="neutral", confidence=0.0)


async def generate_reply(message: str, context: str, tone: str) -> str:
    settings = get_settings()
    client = get_llm_client()
    try:
        system = REPLY_SYSTEM_PROMPT.format(tone=tone)
        response = await client.chat.completions.create(
            model=settings.AI_MODEL_FAST,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Konteks produk:\n{context}\n\nPesan customer:\n{message}",
                },
            ],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content or FALLBACK_REPLY
    except Exception:
        logger.exception("generate_reply error")
        return FALLBACK_REPLY
