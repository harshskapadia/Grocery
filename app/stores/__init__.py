"""Registry of enabled stores. Set GROCERY_STORES=demo to run offline."""
from __future__ import annotations

import os

from .base import Product, Store
from .coles import Coles
from .demo import CATALOG, DemoStore
from .woolworths import Woolworths


def enabled_stores() -> list[Store]:
    choice = os.environ.get("GROCERY_STORES", "live").lower()
    if choice == "demo":
        return [DemoStore(name) for name in CATALOG]
    return [Woolworths(), Coles()]


__all__ = ["Product", "Store", "enabled_stores"]
