"""Coles adapter.

Coles has no official public API. Their site is a Next.js app, so each search
page embeds its results as JSON in a <script id="__NEXT_DATA__"> tag.

Coles uses bot protection. A blocked request often still returns HTTP 200
with a small "check" page, so we detect a block by the missing JSON and report
it rather than trying to get around it. If Coles blocks you, use an authorised
data source instead (see README).
"""
from __future__ import annotations

import json
import re
from urllib.parse import quote_plus

import httpx

from .base import BROWSER_HEADERS, Product, Store

BASE = "https://www.coles.com.au"
IMAGE_BASE = "https://productimages.coles.com.au/productimages"
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


class BlockedError(RuntimeError):
    pass


class Coles(Store):
    name = "Coles"

    async def search(self, query: str, limit: int = 20) -> list[Product]:
        headers = {**BROWSER_HEADERS, "Accept": "text/html,application/xhtml+xml"}
        async with httpx.AsyncClient(headers=headers, timeout=20, follow_redirects=True) as client:
            resp = await client.get(f"{BASE}/search/products?q={quote_plus(query)}")
            resp.raise_for_status()
            return parse(extract_next_data(resp.text))[:limit]


def extract_next_data(html: str) -> dict:
    match = NEXT_DATA.search(html)
    if not match:
        raise BlockedError("Coles returned a bot-check page instead of results (automated access refused)")
    return json.loads(match.group(1))["props"]


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
