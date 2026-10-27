"""Offline fake store so the app and tests work without internet access."""
from __future__ import annotations

from .base import Product, Store

CATALOG = {
    "DemoMart": [
        ("dm-1", "Full Cream Milk", 3.10, "2L", "$1.55 / 1L"),
        ("dm-2", "Free Range Eggs 12 Pack", 6.50, "700g", "$0.93 / 100g"),
        ("dm-3", "White Bread Sandwich Loaf", 2.70, "650g", "$0.42 / 100g"),
        ("dm-4", "Bananas", 4.50, "1kg", "$4.50 / 1kg"),
    ],
    "BudgetGrocer": [
        ("bg-1", "Full Cream Milk", 2.99, "2L", "$1.50 / 1L"),
        ("bg-2", "Free Range Eggs 12 Pack", 6.80, "700g", "$0.97 / 100g"),
        ("bg-3", "White Bread Sandwich Loaf", 2.50, "650g", "$0.38 / 100g"),
    ],
}


class DemoStore(Store):
    def __init__(self, name: str):
        self.name = name

    async def search(self, query: str, limit: int = 20) -> list[Product]:
        words = query.lower().split()
        return [
            Product(self.name, pid, name, price, size, unit)
            for pid, name, price, size, unit in CATALOG.get(self.name, [])
            if all(w in name.lower() for w in words)
        ][:limit]
