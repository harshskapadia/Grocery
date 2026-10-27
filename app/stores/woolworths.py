"""Woolworths adapter.

Woolworths has no official public API. This uses the JSON endpoint their own
website calls. It can change or be blocked at any time, so keep request volume
low and check Woolworths' terms of use before running it at scale.
"""
from __future__ import annotations

import httpx

from .base import BROWSER_HEADERS, Product, Store

BASE = "https://www.woolworths.com.au"


class Woolworths(Store):
    name = "Woolworths"

    async def search(self, query: str, limit: int = 20) -> list[Product]:
        async with httpx.AsyncClient(headers=BROWSER_HEADERS, timeout=20, follow_redirects=True) as client:
            # The API expects the cookies the homepage sets.
            await client.get(BASE)
            resp = await client.get(
                f"{BASE}/apis/ui/Search/products",
                params={"searchTerm": query, "pageSize": limit, "pageNumber": 1, "sortType": "TraderRelevance"},
            )
            resp.raise_for_status()
            if "json" not in resp.headers.get("content-type", ""):
                raise RuntimeError("Woolworths returned a bot-check page instead of results")
            return parse(resp.json())


def parse(data: dict) -> list[Product]:
    products = []
    for group in data.get("Products") or []:
        for p in group.get("Products") or []:
            if p.get("Price") is None:
                continue
            products.append(
                Product(
                    store=Woolworths.name,
                    store_product_id=str(p["Stockcode"]),
                    name=p.get("DisplayName") or p.get("Name", ""),
                    price=float(p["Price"]),
                    size=p.get("PackageSize"),
                    unit_price=p.get("CupString"),
                    was_price=p.get("WasPrice"),
                    image_url=p.get("MediumImageFile") or p.get("SmallImageFile"),
                    url=f"{BASE}/shop/productdetails/{p['Stockcode']}/{p.get('UrlFriendlyName', '')}",
                    available=bool(p.get("IsAvailable", True)),
                )
            )
    return products
