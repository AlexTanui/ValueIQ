"""Load the supplied task files (plus API sales) into clean properties and sales.

- properties: the official input file (181,711 IDs) with a building key, parsed
  unit number, floor, address-type flags, mesh-block and location features.
  Unit attributes come only from the supplied file, never from current API fields.
- sales: union of confirmed flat sales (supplied), API unit sales and both legs
  of the supplied repeat-sale pairs, on or before the valuation date, deduplicated
  by (gnaf_id, date) with supplied sales preferred, and with bulk / en-bloc sales removed.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.location import LOCATION_FEATURES, add_location_features

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TASK_DIR = DATA_DIR / "task5"
VALUATION_DATE = pd.Timestamp("2026-08-31")
CBD = (-33.8675, 151.2070)  # Martin Place

MIN_PRICE, MAX_PRICE = 100_000, 20_000_000
BULK_GROUP_SIZE = 3
SOURCE_PRIORITY = {"flat_sales": 0, "api": 1, "repeat": 2}

BLOCK_FEATURES = ["mb_homes_2021", "mb_people_per_home_2021", "mb_new_homes", "mb_new_home_share"]
PROPERTY_COLUMNS = (["gnaf_pid", "building_key", "addr_prefix", "unit_no", "floor_est", "flats_in_building",
                     "mb", "api_suburb", "block_type", "is_commercial", "is_carspace", "dist_cbd_km",
                     "lat", "lng"] + LOCATION_FEATURES + BLOCK_FEATURES)


def _building_key(address, suburb):
    return f"{address.rsplit(',', 1)[-1].strip().upper()}|{suburb}"


def _floor(address, unit_no, flats):
    """'Level 12' in the address, else hundreds-style unit numbers (1205 -> 12)
    in buildings with 20+ flats, else missing."""
    m = re.search(r"\bLevel\s+(\d+)", address, flags=re.I)
    if m:
        return float(m.group(1))
    if pd.notna(unit_no) and unit_no >= 100 and flats >= 20:
        return float(unit_no // 100)
    return np.nan


def load_properties():
    p = pd.read_csv(TASK_DIR / "flats-city-of-sydney.csv", dtype={"gnaf_id": str, "unit_number": str})
    p = p.rename(columns={"gnaf_id": "gnaf_pid", "suburb": "api_suburb", "latitude": "lat", "longitude": "lng"})
    p["building_key"] = [_building_key(a, s) for a, s in zip(p["address"], p["api_suburb"])]
    p["addr_prefix"] = np.where(p["address"].str.contains(","),
                                p["address"].str.extract(r"^([A-Za-z ]+?)\s*[\dA-Z]*\d", expand=False)
                                .fillna("").str.strip().str.upper(), "")
    p["unit_no"] = pd.to_numeric(p["unit_number"].str.extract(r"(\d+)", expand=False), errors="coerce")
    p["floor_est"] = [_floor(a, u, f) for a, u, f in zip(p["address"], p["unit_no"], p["flats_in_building"])]
    addr = p["address"].str.upper()
    p["is_commercial"] = addr.str.contains(r"\b(?:SHOP|OFFICE|SUITE)\b")
    p["is_carspace"] = addr.str.contains(r"\b(?:CARSPACE|CAR SPACE|PARKING)\b")
    p["dist_cbd_km"] = _haversine_km(p["lat"], p["lng"], *CBD)
    p = add_location_features(p)

    b = pd.read_csv(TASK_DIR / "blocks-homes-and-people-2021-2026.csv")
    b = pd.DataFrame({
        "mb": b["mb"], "mb_homes_2021": b["homes_2021"],
        "mb_people_per_home_2021": b["people_2021"] / b["homes_2021"].where(b["homes_2021"] > 0),
        "mb_new_homes": b["new_homes"],
        "mb_new_home_share": b["new_homes"] / b["homes_2026"].where(b["homes_2026"] > 0),
    })
    return p.merge(b, on="mb", how="left")


def _supplied_sales():
    fs = pd.read_csv(TASK_DIR / "flat-sales-city-of-sydney.csv", dtype={"gnaf_id": str}, parse_dates=["sold_date"])
    fs = fs.rename(columns={"gnaf_id": "gnaf_pid", "price": "sold_price"})
    fs = fs[["gnaf_pid", "sold_date", "sold_price", "bedrooms", "bathrooms", "car_spaces"]].assign(source="flat_sales")

    rs = pd.read_csv(TASK_DIR / "repeat-sales-city-of-sydney.csv", dtype={"gnaf_pid": str},
                     parse_dates=["buy_date", "sell_date"])
    legs = pd.concat([
        rs[["gnaf_pid", "buy_date", "buy_price"]].set_axis(["gnaf_pid", "sold_date", "sold_price"], axis=1),
        rs[["gnaf_pid", "sell_date", "sell_price"]].set_axis(["gnaf_pid", "sold_date", "sold_price"], axis=1),
    ]).assign(source="repeat")
    return fs, legs


def _api_sales():
    s = pd.read_csv(DATA_DIR / "api_sales.csv", parse_dates=["sold_date"], low_memory=False)
    s = s[s["property_type"].eq("Unit")]
    return s[["gnaf_pid", "sold_date", "sold_price", "bedrooms", "bathrooms", "car_spaces"]].assign(source="api")


def load_sales(properties):
    fs, legs = _supplied_sales()
    parts = [fs, legs]
    if (DATA_DIR / "api_sales.csv").exists():
        parts.append(_api_sales())
    s = pd.concat(parts, ignore_index=True)
    s = s[(s["sold_date"] <= VALUATION_DATE) & s["gnaf_pid"].isin(properties["gnaf_pid"])]

    # Keep one record per flat per day, preferring confirmed supplied flat sales.
    s["_prio"] = s["source"].map(SOURCE_PRIORITY)
    s = s.sort_values("_prio").drop_duplicates(["gnaf_pid", "sold_date"]).drop(columns="_prio")

    s = s.merge(properties[PROPERTY_COLUMNS + ["bedrooms", "bathrooms", "car_spaces"]]
                .rename(columns={"bedrooms": "p_bed", "bathrooms": "p_bath", "car_spaces": "p_car"}),
                on="gnaf_pid", how="inner")
    # Bulk / en-bloc: the same price on the same day across 3+ flats in one building.
    grp = s.groupby(["building_key", "sold_date", "sold_price"])["gnaf_pid"].transform("size")
    s = s[(grp < BULK_GROUP_SIZE) & s["sold_price"].between(MIN_PRICE, MAX_PRICE)].copy()

    # Sale-time attributes where recorded, else the supplied property attributes.
    s["bedrooms"] = s["bedrooms"].fillna(s["p_bed"])
    s["bathrooms"] = s["bathrooms"].fillna(s["p_bath"])
    s["car_spaces"] = s["car_spaces"].fillna(s["p_car"])
    s = s.drop(columns=["p_bed", "p_bath", "p_car"]).sort_values("sold_date").reset_index(drop=True)
    s["log_price"] = np.log(s["sold_price"])
    return s


def _haversine_km(lat, lng, lat0, lng0):
    lat, lng = np.radians(lat), np.radians(lng)
    lat0, lng0 = np.radians(lat0), np.radians(lng0)
    a = np.sin((lat - lat0) / 2) ** 2 + np.cos(lat) * np.cos(lat0) * np.sin((lng - lng0) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


if __name__ == "__main__":
    props = load_properties()
    sales = load_sales(props)
    print(f"properties: {len(props):,}  buildings: {props['building_key'].nunique():,}")
    print(f"commercial-flagged: {props['is_commercial'].sum():,}  carspace: {props['is_carspace'].sum():,}")
    print(f"floor_est coverage: {props['floor_est'].notna().mean():.1%}  mb block data: {props['mb_homes_2021'].notna().mean():.1%}")
    print(f"clean sales: {len(sales):,}  ({sales['sold_date'].min().date()} to {sales['sold_date'].max().date()})")
    print(sales["source"].value_counts().to_string())
