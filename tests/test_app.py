import asyncio

import pytest

from app import db
from app.compare import compare
from app.stores import coles, woolworths
from app.stores.demo import CATALOG, DemoStore


@pytest.fixture
def conn(tmp_path):
    return db.connect(str(tmp_path / "test.db"))


def demo_stores():
    return [DemoStore(name) for name in CATALOG]


def test_compare_picks_cheapest_store(conn):
    result = asyncio.run(compare("milk", conn, demo_stores()))
    row = result["results"][0]
    assert row["cheapest_store"] == "BudgetGrocer"
    assert row["cheapest_price"] == 2.99
    assert row["saving"] == pytest.approx(0.11)
    assert len(row["offers"]) == 2
    assert all(o["id"] for o in row["offers"])


def test_price_history_only_records_changes(conn, monkeypatch):
    asyncio.run(compare("milk", conn, demo_stores()))
    asyncio.run(compare("milk", conn, demo_stores()))  # same price -> no new row
    monkeypatch.setitem(CATALOG, "BudgetGrocer", [("bg-1", "Full Cream Milk", 3.20, "2L", None)])
    result = asyncio.run(compare("milk", conn, demo_stores()))
    bg = next(o for o in result["results"][0]["offers"] if o["store"] == "BudgetGrocer")
    assert [h["price"] for h in db.price_history(conn, bg["id"])] == [2.99, 3.20]


def test_failing_store_is_reported_not_fatal(conn):
    class Broken(DemoStore):
        async def search(self, query, limit=20):
            raise RuntimeError("blocked")

    result = asyncio.run(compare("milk", conn, [DemoStore("DemoMart"), Broken("Broken")]))
    assert result["errors"] == {"Broken": "RuntimeError: blocked"}
    assert result["results"]


def test_watches(conn):
    db.add_watch(conn, "milk")
    db.add_watch(conn, "milk")
    db.add_watch(conn, "eggs")
    assert db.list_watches(conn) == ["milk", "eggs"]
    db.remove_watch(conn, "milk")
    assert db.list_watches(conn) == ["eggs"]


def test_woolworths_parser():
    data = {"Products": [{"Products": [{
        "Stockcode": 123, "DisplayName": "Woolworths Milk 2L", "Price": 3.1,
        "PackageSize": "2L", "CupString": "$1.55 / 1L", "UrlFriendlyName": "woolworths-milk-2l",
        "IsAvailable": True, "WasPrice": 3.1,
    }]}]}
    [p] = woolworths.parse(data)
    assert (p.store_product_id, p.price, p.unit_price) == ("123", 3.1, "$1.55 / 1L")
    assert p.url.endswith("/123/woolworths-milk-2l")


def test_coles_parser():
    data = {"pageProps": {"searchResults": {"results": [
        {"_type": "PRODUCT", "id": 456, "brand": "Coles", "name": "Full Cream Milk", "size": "2L",
         "pricing": {"now": 3.1, "was": 0, "comparable": "$1.55 per 1L"},
         "imageUris": [{"uri": "/4/456.jpg"}]},
        {"_type": "SINGLE_TILE"},
    ]}}}
    [p] = coles.parse(data)
    assert (p.name, p.price, p.was_price) == ("Coles Full Cream Milk", 3.1, None)
    assert p.url.endswith("coles-full-cream-milk-2l-456")
