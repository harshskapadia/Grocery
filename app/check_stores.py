"""Check that the real store connections work from this computer.

    python -m app.check_stores            # searches "milk"
    python -m app.check_stores "tim tams"
"""
from __future__ import annotations

import asyncio
import sys
import time

from .stores import Coles, Woolworths


async def check(query: str) -> int:
    failures = 0
    for store in (Woolworths(), Coles()):
        start = time.monotonic()
        try:
            products = await store.search(query, limit=5)
        except Exception as e:
            failures += 1
            print(f"✗ {store.name}: {type(e).__name__}: {e}")
            continue
        took = time.monotonic() - start
        print(f"✓ {store.name}: {len(products)} results in {took:.1f}s")
        for p in products[:3]:
            print(f"    ${p.price:>6.2f}  {p.name} {p.size or ''}  ({p.unit_price or '-'})")
    return failures


if __name__ == "__main__":
    sys.exit(asyncio.run(check(" ".join(sys.argv[1:]) or "milk")))
