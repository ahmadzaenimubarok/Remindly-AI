# Remindly AI

AI-powered customer engagement platform for Indonesian UMKM resellers. Automates Facebook Messenger and Instagram DM replies, comment responses, and lead classification using AI.

### Supported Channels

| Channel | Status |
|---------|--------|
| Facebook Messenger (DM) | ✅ Live |
| Facebook Page Comments | ✅ Live |
| Instagram DM | ✅ Live |
| WhatsApp Business | 🔜 Coming Soon |
| TikTok | 🔜 Coming Soon |
| Shopify (Product Import) | 🔜 Coming Soon |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.12 |
| Frontend | React 19 + Vite + Tailwind + shadcn/ui |
| Database | PostgreSQL + pgvector |
| Queue | Redis + Celery |
| AI | OpenRouter (Llama 3.1) |
| Billing | Stripe |
| Integrations | Facebook Messenger, Instagram DM |
| Tunnel | Cloudflare Tunnel |

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- Cloudflare account (for tunnel)

## Setup

### 1. Database

```bash
sudo -u postgres createdb reseller_ai
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '1';"
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment variables
cp .env.example .env

# Edit .env — fill in all secret keys (see Environment Variables below)

# Run database migrations
alembic upgrade head

# Seed demo data
python scripts/seed.py

# Start backend
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

Backend available at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend available at `http://localhost:5173`. Vite automatically proxies `/api` to `localhost:8000`.

### 4. Celery Worker

```bash
cd backend
source .venv/bin/activate

celery -A workers.celery_app worker --loglevel=info -Q celery,engagement,discovery,content,conversion,leads
```

**Important**: The `-Q` flag is required with all queues. Without it, the worker only consumes from the default `celery` queue, but engagement tasks are routed to the `engagement` queue.

### 5. Seed Stripe (optional)

```bash
cd backend
python scripts/seed_stripe.py
```

Creates Stripe products and prices for Starter (Rp99k/mo), Pro (Rp299k/mo), and Enterprise (Rp2,999k/yr) plans.

## Environment Variables

### Backend `.env`

```ini
# App
APP_ENV=development
APP_SECRET_KEY=<random-32-chars>

# Database
DATABASE_URL=postgresql+asyncpg://postgres:1@localhost:5432/reseller_ai

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Provider
OPENROUTER_API_KEY=sk-or-v1-<your-key>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL_FAST=meta-llama/llama-3.1-8b-instruct
AI_MODEL_QUALITY=meta-llama/llama-3.1-8b-instruct

# Meta (Facebook)
META_APP_ID=<your-app-id>
META_APP_SECRET=<your-app-secret>
META_VERIFY_TOKEN=reseller-ai-webhook-verify-secret
META_REDIRECT_URI=https://<your-domain>/api/v1/auth/facebook/callback
META_IG_REDIRECT_URI=https://<your-domain>/api/v1/auth/instagram/callback
FRONTEND_URL=https://<your-domain>

# Encryption
CREDENTIAL_ENCRYPTION_KEY=<fernet-key-44-chars>

# Stripe
STRIPE_SECRET_KEY=sk_test_<your-key>
STRIPE_WEBHOOK_SECRET=whsec_<your-secret>
```

Generate a Fernet key:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Frontend `.env`

```ini
VITE_USE_DEMO_DATA=false
```

## Production (Single Domain)

On the server, frontend and backend are served from a **single domain** via Cloudflare Tunnel.

### Architecture

```
User → Cloudflare → Cloudflare Tunnel → Server
                                           ├── /api/*  → uvicorn (port 8000)
                                           └── /*      → nginx (port 8080) → frontend static
```

### Build Frontend

```bash
cd frontend
npm run build
```

Output is in `frontend/dist/`.

### Nginx Config

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend static files
    location / {
        root /home/px/Projects/Reseller/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Webhooks (Facebook/Instagram)
    location /webhooks/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### Cloudflare Tunnel

```bash
cloudflared tunnel create <tunnel-name>
```

~/.cloudflared/config.yml:
```yaml
tunnel: <tunnel-id>
credentials-file: /home/px/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: your-domain.com
    service: http://localhost:8080
  - service: http_status:404
```

```bash
cloudflared tunnel run <tunnel-name>
```

### Update Backend Config for Production

In `backend/.env`:
```ini
META_REDIRECT_URI=https://your-domain.com/api/v1/auth/facebook/callback
META_IG_REDIRECT_URI=https://your-domain.com/api/v1/auth/instagram/callback
FRONTEND_URL=https://your-domain.com
```

In `backend/app/main.py`, add production domain to CORS:
```python
allow_origins=["http://localhost:5173", "https://your-domain.com"],
```

In Facebook Developer Console:
- **Valid OAuth Redirect URIs**: `https://your-domain.com/api/v1/auth/facebook/callback`, `https://your-domain.com/api/v1/auth/instagram/callback`
- **Webhooks Callback URL**: `https://your-domain.com/webhooks/facebook`

## Testing

### Run All Tests

```bash
cd backend
pytest
```

### Manual Webhook Test

```bash
cd backend
python -c "
import httpx, json, hmac, hashlib
from app.core.config import get_settings

settings = get_settings()
payload = {'object': 'page', 'entry': [{'id': 'YOUR_PAGE_ID', 'time': 1720000000, 'messaging': [{'sender': {'id': 'TEST_SENDER_ID'}, 'recipient': {'id': 'YOUR_PAGE_ID'}, 'timestamp': 1720000000, 'message': {'mid': 'test_001', 'text': 'Hello, is this in stock?'}}]}]}
body = json.dumps(payload).encode()
sig = 'sha256=' + hmac.new(settings.META_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
resp = httpx.post('http://localhost:8000/webhooks/facebook', content=body, headers={'Content-Type': 'application/json', 'X-Hub-Signature-256': sig})
print(resp.status_code, resp.json())
"
```

## Facebook Webhook Setup

1. Open [Meta Developer Console](https://developers.facebook.com)
2. App → Messenger → Settings → Webhooks
3. Enter Callback URL: `https://your-domain.com/webhooks/facebook`
4. Enter Verify Token: `reseller-ai-webhook-verify-secret`
5. Click **Verify and Save**
6. Check: `messages`, `messaging_postbacks`, `feed`
7. **Important**: Add your Page to the App at App Dashboard → Settings → Facebook Pages → Add Page ID
8. Subscribe Page from the dropdown

**Note**: Facebook does not send webhooks for Page admin/editor messages. For testing, use a different Facebook account as a tester (App Dashboard → Roles → People → Add People → Tester).

## Project Structure

```
backend/
├── app/
│   ├── core/           # Config, database, security, feature flags
│   ├── middleware/      # Tenant context, rate limiter, error handler
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic validation schemas
│   ├── routers/        # API endpoints (auth, billing, conversations, webhooks, ...)
│   └── services/       # Business logic (facebook, instagram, engagement, billing, ...)
├── workers/            # Celery task workers
├── alembic/            # Database migrations
├── scripts/            # Seed data scripts
└── tests/              # Test suite

frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── hooks/          # React hooks (useAuth, useConversations, etc.)
│   ├── pages/          # Page components (Inbox, Leads, Settings, Billing, ...)
│   ├── store/          # Zustand state management
│   └── lib/            # API client, utilities
└── dist/               # Production build output

docs/
└── superpowers/
    ├── plans/          # Implementation plans per phase
    └── specs/          # Design specifications
```

### Upcoming Integrations

| Integration | Status | Plan Document |
|-------------|--------|---------------|
| Shopify product import | Planning | `docs/superpowers/plans/2026-07-13-shopify-product-integration.md` |
| WhatsApp Business | Planned | — |
| TikTok | Planned | — |

## Demo Credentials

| Field | Value |
|-------|-------|
| Email | `admin@demo.com` |
| Password | `demo1234` |
| Tenant | Demo Toko |
| Plan | Pro |
