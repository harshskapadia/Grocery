"""Common interface every store adapter implements."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-AU,en;q=0.9",
}


@dataclass
class Product:
    store: str
    store_product_id: str
    name: str
    price: float
    size: Optional[str] = None
    unit_price: Optional[str] = None  # e.g. "$1.55 / 1L" as shown by the store
    was_price: Optional[float] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    available: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class Store:
    """Subclass this to add a new supermarket."""

    name: str = "store"

    async def search(self, query: str, limit: int = 20) -> list[Product]:
        raise NotImplementedError
