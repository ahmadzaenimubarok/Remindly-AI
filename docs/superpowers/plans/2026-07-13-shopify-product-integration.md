# Plan: Shopify Product Integration

**Tanggal:** 13 Juli 2026
**Status:** Draft
**Fase:** 5a — Marketplace Integration

---

## Ringkasan

Menambahkan integrasi ke Shopify untuk mengambil produk dari toko Shopify tenant. Ini memungkinkan otomatisasi import produk ke dalam sistem Remindly AI, sehingga konteks RAG untuk AI reply bisa langsung dari katalog Shopify tanpa input manual.

---

## Scope

### In Scope
- OAuth flow untuk connect Shopify store
- Fetch produk dari Shopify Admin API (title, description, price, images, variants)
- Auto-import produk ke tabel `products` + generate embedding ke `product_embeddings` (pgvector)
- Sync produk: manual trigger + optional scheduled sync
- UI: Shopify connect card di Settings, import trigger di Products page

### Out of Scope
- Shopify order management
- Shopify inventory/stock sync
- Shopify webhook untuk real-time product updates (fase berikutnya)
- Shopify checkout/payment integration

---

## Arsitektur

### 1. Shopify OAuth Flow

```
1. Tenant klik "Connect Shopify" di Settings
        ↓
2. Backend generate OAuth URL:
   https://{shop}.myshopify.com/admin/oauth/authorize
     ?client_id={SHOPIFY_API_KEY}
     &scope=read_products,read_inventory
     &redirect_uri={SHOPIFY_REDIRECT_URI}
     &state={tenant_id}   ← anti-CSRF
        ↓
3. Tenant login ke Shopify & grant izin
        ↓
4. Shopify redirect ke: GET /api/v1/auth/shopify/callback?code=...&state={shop}.myshopify.com
        ↓
5. Backend tukar code → access token
   (POST https://{shop}.myshopify.com/admin/oauth/access_token)
        ↓
6. Simpan terenkripsi di tenant_credentials:
   {
     tenant_id,
     platform: "shopify",
     access_token_encrypted: encrypt(access_token),
     metadata: { shop_domain, shop_name }
   }
        ↓
7. FeatureStatus "shopify_import" → ACTIVE
```

### 2. Product Fetch Flow

```
1. Tenant klik "Import from Shopify" di Products page
   (atau trigger manual dari Settings)
        ↓
2. Backend cek feature status: check_feature_status(tenant_id, "shopify_import", db)
        ↓
3. Fetch produk dari Shopify Admin API:
   GET https://{shop}.myshopify.com/admin/api/2024-01/products.json
   ?limit=250
   Headers: X-Shopify-Access-Token: {decrypted_token}
        ↓
4. Upsert produk ke tabel products:
   - Match by shopify_product_id (kolom baru)
   - Update name, description, base_price, images
   - Set source = 'shopify'
        ↓
5. Generate embedding untuk setiap produk:
   - Gabungkan: title + description + tags
   - Call openai_service.embed()
   - Upsert ke product_embeddings (content_type = 'product')
        ↓
6. Return summary: X produk diimport, Y produk diupdate
```

### 3. Database Changes

```sql
-- Tambah kolom ke products
ALTER TABLE products ADD COLUMN shopify_product_id VARCHAR(50);
ALTER TABLE products ADD COLUMN shopify_synced_at TIMESTAMPTZ;
ALTER TABLE products ADD COLUMN source VARCHAR(20) DEFAULT 'manual';  -- 'manual' | 'shopify'

-- Index untuk dedup
CREATE UNIQUE INDEX idx_products_shopify_id ON products(tenant_id, shopify_product_id)
  WHERE shopify_product_id IS NOT NULL;
```

### 4. Env Variables

```bash
# Shopify
SHOPIFY_API_KEY=
SHOPIFY_API_SECRET=
SHOPIFY_REDIRECT_URI=https://your-domain.com/api/v1/auth/shopify/callback
```

---

## API Endpoints

### Backend

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| GET | `/api/v1/auth/shopify/login` | Generate OAuth URL, redirect ke Shopify |
| GET | `/api/v1/auth/shopify/callback` | Handle callback, tukar code → token, simpan credential |
| POST | `/api/v1/settings/shopify/connect` | Manual connect (shop_domain + access_token) |
| DELETE | `/api/v1/settings/shopify/disconnect` | Hapus credential Shopify |
| POST | `/api/v1/products/shopify/import` | Trigger import produk dari Shopify |
| GET | `/api/v1/settings/shopify/status` | Status koneksi Shopify |

### Frontend

| Component | Fungsi |
|-----------|--------|
| `Settings.tsx` | Shopify connect card (sama pattern dengan FB/IG) |
| `Products.tsx` | Tombol "Import from Shopify" + last sync timestamp |
| `useShopifyOAuth.ts` | Hook untuk OAuth flow |
| `useShopifyImport.ts` | Hook untuk trigger import |

---

## File Structure (New/Modified)

### New Files
```
backend/
├── app/
│   ├── services/
│   │   ├── shopify_service.py          # Shopify Admin API client
│   │   └── shopify_oauth_service.py    # OAuth token exchange
│   ├── routers/
│   │   └── shopify_oauth.py            # OAuth routes
│   └── schemas/
│       └── shopify.py                  # Pydantic schemas
├── workers/
│   └── shopify_worker.py               # Celery task untuk product sync

frontend/
├── src/
│   ├── pages/
│   │   └── ShopifyConnect.tsx          # OAuth initiation page
│   │   └── ShopifyCallback.tsx         # OAuth callback page
│   └── hooks/
│       └── useShopifyOAuth.ts          # OAuth flow hook
```

### Modified Files
```
backend/
├── app/core/config.py                  # +SHOPIFY_API_KEY, SHOPIFY_API_SECRET, SHOPIFY_REDIRECT_URI
├── app/models/product.py               # +shopify_product_id, shopify_synced_at, source
├── app/routers/settings.py             # +shopify status/disconnect
├── app/services/product_service.py     # +import_from_shopify()
├── backend/.env.example                # +Shopify env vars

frontend/
├── src/pages/Settings.tsx              # +Shopify connect card
├── src/pages/Products.tsx              # +Import from Shopify button
```

---

## Implementation Phases

### Phase 1: Foundation (Est. 2-3 hours)
- [ ] Add Shopify env vars to config.py + .env.example
- [ ] Create Shopify OAuth service (token exchange)
- [ ] Create Shopify OAuth router (login, callback)
- [ ] Alembic migration: add shopify columns to products

### Phase 2: Product Fetch (Est. 3-4 hours)
- [ ] Create Shopify service (Admin API client)
- [ ] Implement product fetch + upsert logic
- [ ] Generate embeddings for imported products
- [ ] Create Celery task for async import
- [ ] API endpoint: POST /products/shopify/import

### Phase 3: Frontend (Est. 2-3 hours)
- [ ] ShopifyConnect.tsx page
- [ ] ShopifyCallback.tsx page
- [ ] useShopifyOAuth.ts hook
- [ ] Settings.tsx: add Shopify card
- [ ] Products.tsx: add Import button + status

### Phase 4: Polish & Test (Est. 1-2 hours)
- [ ] Error handling (rate limits, invalid shop, expired tokens)
- [ ] Tests for shopify_service, shopify_oauth_service
- [ ] Tests for product import flow
- [ ] Feature flag: shopify_import per plan

---

## Plan Mapping

| Feature | Free | Starter | Pro | Enterprise |
|---------|------|---------|-----|------------|
| `shopify_import` | - | ✓ | ✓ | ✓ |

---

## Risks & Mitigasi

| Risk | Mitigation |
|------|------------|
| Shopify rate limits (40 req/10s) | Batch fetch, respect Retry-After headers |
| Large catalogs (1000+ products) | Pagination, async Celery task, progress indicator |
| Token expiry | Long-lived Admin API tokens (no expiry for offline access) |
| Duplicate import | Upsert by shopify_product_id, idempotent |
| Shopify API version changes | Pin to stable version (2024-01), monitor deprecation |

---

## Reference

- [Shopify OAuth Docs](https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/authorization-code-grant)
- [Shopify Admin API - Products](https://shopify.dev/docs/api/admin-rest/2024-01/resources/product)
- [Shopify API Versioning](https://shopify.dev/docs/api/usage/versioning)
