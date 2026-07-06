# Instagram DM Integration — Design Spec

**Date:** 2026-07-06
**Scope:** Instagram Direct Messages only (comments deferred)
**Approach:** Mirror Facebook pattern, reuse existing shared helpers (Approach C)

---

## Overview

Tambah dukungan Instagram DM ke sistem engagement yang sudah ada. Instagram Business API pakai Meta Graph API yang sama dengan Facebook, sehingga webhook verification, signature check, dan format API call sebagian besar identik. Implementasi mengikuti pola `process_messenger_message` tapi dengan credential platform `"instagram"` terpisah.

---

## Architecture

```
Meta Webhook → POST /webhooks/instagram?tenant_id=...
                    ↓ signature verify (shared _verify_fb_signature)
                    ↓ parse payload (object == "instagram")
                    ↓ extract messaging[] events
                    ↓ process_instagram_event.delay(tenant_id, event)
                              ↓ Celery worker (queue: "engagement")
                              ↓ process_instagram_dm(tenant_id, event, db)
                                        ↓ check feature flag "instagram_reply"
                                        ↓ get credential platform "instagram"
                                        ↓ shared helpers (customer, session, intent, escalation)
                                        ↓ instagram_service.send_instagram_dm()
                                        ↓ save Conversation + SystemLog
                                        ↓ classify_lead.delay()
```

---

## Components

### 1. `routers/webhooks.py` — dua endpoint baru

**GET /webhooks/instagram**
- Verifikasi webhook Meta (dipanggil sekali saat setup di Meta Developer Console)
- Pakai `META_VERIFY_TOKEN` yang sama dengan Facebook (satu Meta App)
- Pakai fungsi `_verify_fb_signature` yang sudah ada

**POST /webhooks/instagram**
- Query param: `tenant_id` (UUID)
- Signature verify via `_verify_fb_signature` + header `X-Hub-Signature-256`
- Filter: `payload.object == "instagram"`
- Ekstrak DM dari `entry[].messaging[]` — skip jika `is_echo: true`
- Event dict: `{channel_type: "dm", message_id, message, sender_id}`
- Queue ke `process_instagram_event.delay(tenant_id, event)`
- Return `{status: "ok", queued: N}`

Schema: pakai `FacebookWebhookPayload` yang sudah ada (struktur `{object, entry[]}` identik).

### 2. `services/instagram_service.py` — file baru

```
get_instagram_user_name(page_token, igsid) -> str | None
    GET /{igsid}?fields=name,username&access_token=...
    Fallback: name → username → None

send_instagram_dm(page_token, recipient_igsid, message) -> bool
    POST /me/messages
    Body: {recipient: {id: igsid}, message: {text: message}, messaging_type: "RESPONSE"}
    Return True jika success, False jika gagal (log error)
```

Graph API base: `https://graph.facebook.com/v21.0` (sama dengan Facebook).

### 3. `services/engagement_service.py` — tambah `process_instagram_dm`

Fungsi baru, tidak ada perubahan pada fungsi yang sudah ada.

```
process_instagram_dm(tenant_id, event, db) -> str | None
    event keys: message_id, message, sender_id

    1. check_feature_status(tenant_id, "instagram_reply", db)
    2. _get_tenant(tenant_id, db)
    3. _get_instagram_credential(tenant_id, db)  ← fetch platform="instagram"
    4. dedup via _get_conversation_by_platform_id(tenant_id, message_id, db)
    5. get_instagram_user_name(page_token, sender_id)
    6. _get_or_create_customer(tenant_id, sender_id, "instagram", name, db)
    7. _get_or_create_session(tenant_id, customer.id, "instagram", "dm", message, db)
    8. get_product_context() → classify_intent() → _should_escalate()
    9. if escalate: save Conversation(is_human_takeover=True), return
   10. generate_reply() → send_instagram_dm()
   11. save Conversation, check _is_closing_signal(), save SystemLog
   12. return str(customer.id)
```

Tambah helper private `_get_instagram_credential` (identik dengan `_get_facebook_credential` tapi platform `"instagram"`).

### 4. `workers/engagement_worker.py` — tambah `process_instagram_event`

Task Celery baru, tidak ada perubahan pada `process_facebook_event`.

```python
@celery_app.task(
    name="workers.engagement_worker.process_instagram_event",
    queue="engagement",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_instagram_event(self, tenant_id: str, event: dict) -> None:
    # Hanya handle channel_type="dm" untuk sekarang
    # Struktur identik dengan process_facebook_event
    # Panggil process_instagram_dm() dari engagement_service
    # Setelah selesai: classify_lead.delay() jika customer_id tidak None
```

---

## Data Model

Tidak ada perubahan schema DB. `TenantCredential` sudah support platform string arbitrary:
- Tenant credential disimpan dengan `platform = "instagram"`
- `Conversation` disimpan dengan `platform = "instagram"`, `channel_type = "dm"`
- `Customer` disimpan dengan `platform = "instagram"`
- `Session` disimpan dengan `platform = "instagram"`, `channel_type = "dm"`

---

## Config & Credentials

Tidak ada perubahan `.env` atau `config.py`. Instagram pakai Meta App yang sama.

Tenant connect Instagram dengan input token manual via settings (platform `"instagram"`). Jika token sama dengan Facebook tidak masalah — disimpan sebagai dua entri credential terpisah.

---

## Feature Flags

`"instagram_reply"` sudah ada di `PLAN_FEATURES`:
- `free`: ✓
- `starter`: ✓
- `pro`: ✓
- `enterprise`: ✓ (wildcard)

---

## Error Handling

| Kondisi | Handling |
|---|---|
| Signature invalid | HTTP 403 |
| Payload invalid | HTTP 400 |
| `object != "instagram"` | `{status: "ignored"}` |
| Tenant tidak ditemukan | return None, log error |
| Credential tidak ada / expired | skip + SystemLog |
| Message sudah diproses (dedup) | return None |
| API call gagal | `sent=False`, Conversation disimpan tanpa `message_out` |
| Escalation | Conversation `is_human_takeover=True`, no reply sent |

---

## Files Changed

| File | Action |
|---|---|
| `backend/app/routers/webhooks.py` | Edit — tambah 2 endpoint |
| `backend/app/services/instagram_service.py` | Create |
| `backend/app/services/engagement_service.py` | Edit — tambah `_get_instagram_credential` + `process_instagram_dm` |
| `backend/workers/engagement_worker.py` | Edit — tambah `process_instagram_event` |

---

## Out of Scope

- Instagram Comment reply (deferred)
- OAuth flow untuk Instagram token
- Frontend UI untuk connect Instagram account
