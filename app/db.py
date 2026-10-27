"""SQLite storage: products, their price history, and watched searches."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from .stores import Product

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    store TEXT NOT NULL,
    store_product_id TEXT NOT NULL,
    name TEXT NOT NULL,
    size TEXT,
    image_url TEXT,
    url TEXT,
    UNIQUE (store, store_product_id)
);
CREATE TABLE IF NOT EXISTS prices (
    product_id INTEGER NOT NULL REFERENCES products(id),
    price REAL NOT NULL,
    unit_price TEXT,
    was_price REAL,
    seen_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS prices_product ON prices (product_id, seen_at);
CREATE TABLE IF NOT EXISTS watches (
    query TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or os.environ.get("GROCERY_DB", "grocery.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_product(conn: sqlite3.Connection, p: Product) -> int:
    """Upsert the product and add a price row only when the price changed."""
    conn.execute(
        """INSERT INTO products (store, store_product_id, name, size, image_url, url)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT (store, store_product_id) DO UPDATE SET
             name = excluded.name, size = excluded.size,
             image_url = excluded.image_url, url = excluded.url""",
        (p.store, p.store_product_id, p.name, p.size, p.image_url, p.url),
    )
    product_id = conn.execute(
        "SELECT id FROM products WHERE store = ? AND store_product_id = ?",
        (p.store, p.store_product_id),
    ).fetchone()["id"]
    last = conn.execute(
        "SELECT price FROM prices WHERE product_id = ? ORDER BY seen_at DESC, rowid DESC LIMIT 1",
        (product_id,),
    ).fetchone()
    if last is None or last["price"] != p.price:
        conn.execute(
            "INSERT INTO prices (product_id, price, unit_price, was_price, seen_at) VALUES (?, ?, ?, ?, ?)",
            (product_id, p.price, p.unit_price, p.was_price, now()),
        )
    conn.commit()
    return product_id


def price_history(conn: sqlite3.Connection, product_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT price, unit_price, was_price, seen_at FROM prices WHERE product_id = ? ORDER BY seen_at, rowid",
        (product_id,),
    )
    return [dict(r) for r in rows]


def add_watch(conn: sqlite3.Connection, query: str) -> None:
    conn.execute("INSERT OR IGNORE INTO watches (query, created_at) VALUES (?, ?)", (query, now()))
    conn.commit()


def remove_watch(conn: sqlite3.Connection, query: str) -> None:
    conn.execute("DELETE FROM watches WHERE query = ?", (query,))
    conn.commit()


def list_watches(conn: sqlite3.Connection) -> list[str]:
    return [r["query"] for r in conn.execute("SELECT query FROM watches ORDER BY created_at")]
