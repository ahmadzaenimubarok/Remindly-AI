import logging
from datetime import datetime, timezone

import httpx

from app.services.shopify_oauth_service import SHOPIFY_API_VERSION

logger = logging.getLogger(__name__)


async def fetch_products(shop_domain: str, access_token: str) -> list[dict]:
    """Fetch produk dari Shopify Admin API dengan pagination."""
    products = []
    url = f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/products.json?limit=250&fields=id,title,body_html,product_type,status,tags,handle,variants,images"

    try:
        with httpx.Client(timeout=30.0) as client:
            while url:
                response = client.get(
                    url,
                    headers={"X-Shopify-Access-Token": access_token},
                )
                if not response.is_success:
                    logger.error(f"fetch_products failed: {response.status_code} {response.text}")
                    break

                data = response.json()
                products.extend(data.get("products", []))

                # Check for pagination (Link header)
                link_header = response.headers.get("Link", "")
                url = None
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        url = part.split(";")[0].strip().strip("<>")
                        break

    except Exception:
        logger.exception("fetch_products error")

    return products


def transform_shopify_product(shopify_product: dict, shop_domain: str) -> dict:
    """Transform data produk dari Shopify format ke internal format."""
    # Get the first variant's price as base_price
    variants = shopify_product.get("variants", [])
    base_price = None
    if variants:
        try:
            base_price = float(variants[0].get("price", 0))
        except (ValueError, TypeError):
            pass

    # Get images
    images = shopify_product.get("images", [])
    image_urls = [img.get("src") for img in images if img.get("src")]

    # Get description (clean HTML)
    body_html = shopify_product.get("body_html", "")

    # Build product URL from handle
    handle = shopify_product.get("handle", "")
    product_url = f"https://{shop_domain}/products/{handle}" if handle else None

    return {
        "shopify_product_id": str(shopify_product.get("id")),
        "name": shopify_product.get("title", ""),
        "description": body_html if body_html else None,
        "base_price": base_price,
        "category": shopify_product.get("product_type", None),
        "status": "active" if shopify_product.get("status") == "active" else "inactive",
        "images": image_urls,
        "tags": shopify_product.get("tags", []),
        "vendor": shopify_product.get("vendor", None),
        "product_type": shopify_product.get("product_type", None),
        "product_url": product_url,
    }


def generate_product_embedding_text(product: dict) -> str:
    """Generate teks untuk embedding dari data produk."""
    parts = [
        product.get("name", ""),
        product.get("description", "") or "",
        product.get("category", "") or "",
        " ".join(product.get("tags", [])),
    ]
    return " ".join(filter(None, parts))
