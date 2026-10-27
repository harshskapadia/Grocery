"""Re-check prices for every watched search.

Run once (for cron / GitHub Actions / Task Scheduler):
    python -m app.refresh
The web server also runs this automatically every REFRESH_HOURS hours.
"""
from __future__ import annotations

import asyncio
import logging
import random

from . import db
from .compare import compare

log = logging.getLogger("grocery.refresh")


async def refresh_all(conn=None) -> dict:
    conn = conn or db.connect()
    summary = {}
    for query in db.list_watches(conn):
        result = await compare(query, conn)
        summary[query] = {"results": len(result["results"]), "errors": result["errors"]}
        log.info("refreshed %r: %s", query, summary[query])
        # Be polite to the store websites: space requests out.
        await asyncio.sleep(random.uniform(2, 5))
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(asyncio.run(refresh_all()))
