"""Coles adapter.

Coles has no official public API. Their site is a Next.js app, so search
results are available as JSON at /_next/data/<buildId>/... . Coles uses
bot protection, so from servers/cloud IPs this often gets blocked (HTTP 403 or a
captcha page). If that happens, run it from a home connection, slow it down, or
swap in a paid scraping API / data provider.
"""
from __future__ import annotations

import re

import httpx

from .base import BROWSER_HEADERS, Product, Store

BASE = "https://www.coles.com.au"
IMAGE_BASE = "https://productimages.coles.com.au/productimages"


class Coles(Store):
    name = "Coles"

    async def search(self, query: str, limit: int = 20) -> list[Product]:
        headers = {**BROWSER_HEADERS, "Accept": "text/html,application/json"}
        async with httpx.AsyncClient(headers=headers, timeout=20, follow_redirects=True) as client:
            home = await client.get(BASE)
            home.raise_for_status()
            match = re.search(r'"buildId":"([^"]+)"', home.text)
            if not match:
                raise RuntimeError("Coles buildId not found (likely blocked by bot protection)")
            resp = await client.get(
                f"{BASE}/_next/data/{match.group(1)}/en/search/products.json",
                params={"q": query},
            )
            resp.raise_for_status()
            return parse(resp.json())[:limit]


def parse(data: dict) -> list[Product]:
    results = (data.get("pageProps") or {}).get("searchResults", {}).get("results") or []
    products = []
    for p in results:
        pricing = p.get("pricing") or {}
        if p.get("_type") != "PRODUCT" or pricing.get("now") is None:
            continue
        name = " ".join(x for x in (p.get("brand"), p.get("name")) if x)
        slug = re.sub(r"[^a-z0-9]+", "-", f"{name} {p.get('size', '')}".lower()).strip("-")
        images = p.get("imageUris") or []
        products.append(
            Product(
                store=Coles.name,
                store_product_id=str(p["id"]),
                name=name,
                price=float(pricing["now"]),
                size=p.get("size"),
                unit_price=pricing.get("comparable"),
                was_price=pricing.get("was") or None,
                image_url=f"{IMAGE_BASE}{images[0]['uri']}" if images else None,
                url=f"{BASE}/product/{slug}-{p['id']}",
                available=bool(p.get("availability", True)),
            )
        )
    return products
