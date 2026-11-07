"""Pull the address list and all pre-cutoff sales for every suburb from the API.

Outputs (git-ignored):
  data/api_properties.csv  -- every home in the 29 suburbs (stand-in for the input CSV)
  data/api_sales.csv       -- every sale dated on or before VALUATION_DATE

Sales are requested with to_date=VALUATION_DATE so post-cutoff sales (the
judging period) are never downloaded, and are filtered again after loading.
"""
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.api.microburbs_client import MicroburbsClient  # noqa: E402

VALUATION_DATE = "2026-08-31"
SALES_FROM = "1990-01-01"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def page_through(client, path, key, params, limit):
    rows, offset = [], 0
    while True:
        data = client.get(path, {**params, "limit": limit, "offset": offset})
        if not data:
            break
        batch = data.get(key) or []
        rows.extend(batch)
        total = data.get("meta", {}).get("total", data.get("total", 0))
        offset += limit
        if not batch or offset >= total:
            break
    return rows


def main():
    logging.basicConfig(level=logging.WARNING)
    client = MicroburbsClient()
    suburbs = [s["suburb"] for s in client.get("/v1/suburbs/list")]

    props, sales = [], []
    for suburb in suburbs:
        p = page_through(client, f"/v1/suburbs/{suburb}/properties", "results", {}, 200)
        s = page_through(
            client, f"/v1/suburbs/{suburb}/sales/recent", "results",
            {"from_date": SALES_FROM, "to_date": VALUATION_DATE}, 200,
        )
        for r in p:
            r["api_suburb"] = suburb
        for r in s:
            r["api_suburb"] = suburb
        props.extend(p)
        sales.extend(s)
        print(f"{suburb:28s} properties={len(p):6d} sales={len(s):6d}", flush=True)

    props = pd.DataFrame(props)
    sales = pd.DataFrame(sales)
    sales["sold_date"] = pd.to_datetime(sales["sold_date"])
    n_before = len(sales)
    sales = sales[sales["sold_date"] <= VALUATION_DATE]
    assert len(sales) == n_before, f"API returned {n_before - len(sales)} post-cutoff sales"

    DATA_DIR.mkdir(exist_ok=True)
    props.to_csv(DATA_DIR / "api_properties.csv", index=False)
    sales.to_csv(DATA_DIR / "api_sales.csv", index=False)
    print(f"\nTotal properties={len(props)} sales={len(sales)} "
          f"(dates {sales['sold_date'].min().date()} to {sales['sold_date'].max().date()})")


if __name__ == "__main__":
    main()
