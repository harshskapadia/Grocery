# Grocery

Search for a grocery product **by name or by photo**, compare prices across
Woolworths, Coles (and any other store you add), see which one is cheapest,
and track how prices change over time.

## How it works

```
 name ─────────────┐
                   ├─► search every store in parallel ─► match same item ─► cheapest + saving
 photo ─► Claude ──┘        (store adapters)              across stores      │
       (vision: "Pauls Milk 2L")                                             ▼
                                                     SQLite: products + price history
                                                                             ▲
                         scheduler (every REFRESH_HOURS) re-runs watched searches
```

| Part | File | What it does |
|---|---|---|
| Store adapters | `app/stores/` | One class per supermarket with `search(query)` → list of products |
| Compare | `app/compare.py` | Queries all stores at once, groups the same item, picks the cheapest |
| Photo search | `app/vision.py` | Sends the photo to Claude, gets back a search term like "Pauls Full Cream Milk 2L" |
| Price history | `app/db.py` | SQLite; a new price row is stored only when the price changes |
| Regular updates | `app/refresh.py` | Re-checks every "watched" search; runs inside the server and can also run from cron |
| Web UI | `app/static/index.html` | Search box, camera/photo upload, comparison table, watchlist |

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Try it offline with two fake stores first:
GROCERY_STORES=demo uvicorn app.main:app --reload
# then open http://localhost:8000

# Real stores (Woolworths + Coles):
uvicorn app.main:app --reload

# Photo search needs an Anthropic API key:
export ANTHROPIC_API_KEY=sk-ant-...
```

Run the tests with `pytest`.

### Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `GROCERY_STORES` | `live` | `live` = Woolworths + Coles, `demo` = offline fake stores |
| `GROCERY_DB` | `grocery.db` | SQLite file path |
| `REFRESH_HOURS` | `6` | How often watched searches are re-checked (`0` turns it off) |
| `ANTHROPIC_API_KEY` | – | Needed only for photo search |

## Keeping prices up to date

1. In the UI, search for something and click **Watch this search**.
2. While the server runs, every `REFRESH_HOURS` it re-searches all watched
   items and records any price changes.
3. If you'd rather not keep the server running, use cron instead
   (set `REFRESH_HOURS=0` on the server):

   ```cron
   # every day at 6:15am
   15 6 * * * cd /path/to/Grocery && .venv/bin/python -m app.refresh
   ```

Supermarket prices mostly change once a week (Wednesday for both Woolworths
and Coles specials), so once or twice a day is plenty.

## Using real Woolworths and Coles prices

Live mode is the default. Run it on your own computer:

```bash
python -m app.check_stores "milk"     # quick test: does each store answer?
uvicorn app.main:app                  # then open http://localhost:8000
```

`check_stores` prints ✓ with a few sample prices for each store that works, or
✗ with the reason it failed.

### Where the data comes from

**Woolworths and Coles don't offer a public price API.** The adapters read the
same data their own websites load. That means:

- **It can break** whenever the sites change. Each adapter is small and
  isolated, and a failing store shows a warning instead of crashing the search.
- **If a store blocks the request** (Coles uses bot protection), the app
  reports "automated access refused" and doesn't try to get around it. Use an
  authorised source for that store instead (below).
- **Check each store's terms of use** before running this publicly or at
  scale. Keep the request rate low (the refresher already pauses between
  searches) and store results instead of hitting the stores for every visitor.
- Prices can differ by state/store location. The adapters use each site's
  default location.

### Authorised data sources (for a public app)

- **Ask the retailer.** Woolworths and Coles both run partner/affiliate
  programs; a data agreement is the only way to be fully in the clear.
- **Licensed grocery-price data providers** that sell Australian supermarket
  price feeds.
- **Third-party scraping services** (e.g. Apify actors for Woolworths/Coles).
  They return the same fields this app uses, so each one is a small adapter in
  `app/stores/`. They still collect the data from the store websites, so the
  terms-of-use question doesn't go away.

## Adding another store (Aldi, IGA, Harris Farm, …)

Create `app/stores/mystore.py`:

```python
from .base import Product, Store

class MyStore(Store):
    name = "MyStore"

    async def search(self, query, limit=20):
        # fetch the store's search results, then:
        return [Product(store=self.name, store_product_id="123",
                        name="Milk 2L", price=3.10, size="2L")]
```

then add it to the list in `app/stores/__init__.py`. Write a `parse()` function
and a parser test with a saved sample response, like the Woolworths/Coles ones
in `tests/test_app.py`.

## Ideas for next steps

- **Barcode scanning**: read the barcode from the photo and match products by
  GTIN — much more accurate than name matching.
- **Price-drop alerts** by email or push when a watched item goes on special.
- **Shopping list mode**: find the cheapest store for a whole basket.
- **Store location**: let users pick their suburb so prices match their store.
- Move from SQLite to Postgres when you deploy for many users.
