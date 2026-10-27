"""Search every store at once and work out where each item is cheapest."""
from __future__ import annotations

import asyncio
import re
import sqlite3
from difflib import SequenceMatcher

from . import db
from .stores import Product, Store, enabled_stores


async def search_all(query: str, stores: list[Store] | None = None, limit: int = 20) -> tuple[list[Product], dict]:
    """Query all stores in parallel. A failing store is reported, not fatal."""
    stores = stores if stores is not None else enabled_stores()
    results = await asyncio.gather(*(s.search(query, limit) for s in stores), return_exceptions=True)
    products: list[Product] = []
    errors: dict[str, str] = {}
    for store, result in zip(stores, results):
        if isinstance(result, BaseException):
            errors[store.name] = f"{type(result).__name__}: {result}"
        else:
            products.extend(result)
    return products, errors


def _key(p: Product) -> str:
    text = f"{p.name} {p.size or ''}".lower()
    return " ".join(sorted(re.findall(r"[a-z0-9.]+", text)))


def group_matches(products: list[Product], threshold: float = 0.8) -> list[list[Product]]:
    """Cluster the same item sold by different stores by name+size similarity.

    Simple fuzzy matching; good enough to start. Matching on barcode (GTIN),
    when a store exposes it, is far more reliable.
    """
    groups: list[tuple[str, list[Product]]] = []
    for p in products:
        k = _key(p)
        for gk, members in groups:
            if SequenceMatcher(None, k, gk).ratio() >= threshold and p.store not in {m.store for m in members}:
                members.append(p)
                break
        else:
            groups.append((k, [p]))
    return [members for _, members in groups]


def build_comparison(products: list[Product]) -> list[dict]:
    rows = []
    for members in group_matches(products):
        members.sort(key=lambda p: p.price)
        cheapest = members[0]
        rows.append(
            {
                "name": cheapest.name,
                "size": cheapest.size,
                "cheapest_store": cheapest.store,
                "cheapest_price": cheapest.price,
                "saving": round(members[-1].price - cheapest.price, 2) if len(members) > 1 else 0.0,
                "offers": [p.to_dict() for p in members],
            }
        )
    # Items found in several stores first (those are the real comparisons), then by price.
    rows.sort(key=lambda r: (-len(r["offers"]), r["cheapest_price"]))
    return rows


async def compare(query: str, conn: sqlite3.Connection | None = None, stores: list[Store] | None = None) -> dict:
    products, errors = await search_all(query, stores)
    db_ids = {}
    if conn is not None:
        # Every search also records today's prices, so history builds up over time.
        db_ids = {(p.store, p.store_product_id): db.save_product(conn, p) for p in products}
    comparison = build_comparison(products)
    for row in comparison:
        for offer in row["offers"]:
            offer["id"] = db_ids.get((offer["store"], offer["store_product_id"]))
    return {"query": query, "results": comparison, "errors": errors}
