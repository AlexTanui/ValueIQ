"""Load the API pulls and produce clean unit addresses and unit sales.

- properties: every Unit-type address, with a building key, parsed unit number,
  estimated floor and address-type flags.
- sales: Unit sales on or before the valuation date, with bulk / en-bloc sales
  (same price, date and location across 3+ units) removed.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.location import LOCATION_FEATURES, add_location_features

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
VALUATION_DATE = pd.Timestamp("2026-08-31")
CBD = (-33.8675, 151.2070)  # Martin Place

MIN_PRICE, MAX_PRICE = 100_000, 20_000_000
BULK_GROUP_SIZE = 3


def _parse_address(address):
    """'SUITE 2/9/88 PHILLIP ST SYDNEY 2000' -> (prefix, unit_no, building)."""
    if "/" not in address:
        return "", np.nan, address
    head, building = address.split("/", 1)[0], address.rsplit("/", 1)[1]
    prefix = re.match(r"^([A-Z ]*?)\s*[A-Z]?\d", head)
    prefix = prefix.group(1).strip() if prefix else ""
    digits = re.search(r"(\d+)", head)
    return prefix, float(digits.group(1)) if digits else np.nan, building


def _estimate_floor(row):
    """Floor from the API when present, else from unit numbers like 1205 -> 12.

    Only trusted when the building is large enough that hundreds-style
    numbering is plausible; otherwise left missing.
    """
    if pd.notna(row["floor"]):
        return row["floor"]
    n, flats = row["unit_no"], row["flats_in_building"]
    if pd.notna(n) and n >= 100 and pd.notna(flats) and flats >= 20:
        return n // 100
    return np.nan


def load_properties(units_only=True):
    p = pd.read_csv(DATA_DIR / "api_properties.csv", low_memory=False)
    if units_only:
        p = p[p["property_type"].eq("Unit")].copy()
    parsed = p["address"].map(_parse_address)
    p["addr_prefix"] = parsed.str[0]
    p["unit_no"] = parsed.str[1]
    p["building_key"] = parsed.str[2]
    p["floor_est"] = p.apply(_estimate_floor, axis=1)
    addr = p["address"].str.upper()
    p["is_commercial"] = addr.str.contains(r"\b(?:SHOP|OFFICE|SUITE)\b") | p["dwelling_type"].isin(
        ["commercial", "industrial"])
    p["is_carspace"] = addr.str.contains(r"\b(?:CARSPACE|CAR SPACE|PARKING)\b")
    p["dist_cbd_km"] = _haversine_km(p["lat"], p["lng"], *CBD)
    p = add_location_features(p.reset_index(drop=True))
    return p


def load_sales(properties):
    s = pd.read_csv(DATA_DIR / "api_sales.csv", parse_dates=["sold_date"], low_memory=False)
    s = s[s["sold_date"] <= VALUATION_DATE]
    s = s[s["property_type"].eq("Unit")].copy()

    grp = s.groupby(["sold_price", "sold_date", "lat", "lng"])["gnaf_pid"].transform("size")
    s = s[grp < BULK_GROUP_SIZE]
    s = s[s["sold_price"].between(MIN_PRICE, MAX_PRICE)]

    keep = ["gnaf_pid", "building_key", "addr_prefix", "unit_no", "floor_est", "flats_in_building",
            "mb", "api_suburb", "dwelling_type", "is_commercial", "is_carspace", "dist_cbd_km"] + LOCATION_FEATURES
    s = s.drop(columns=["api_suburb"]).merge(properties[keep], on="gnaf_pid", how="inner")
    s = s.sort_values("sold_date").reset_index(drop=True)
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
    print(f"unit properties: {len(props):,}  buildings: {props['building_key'].nunique():,}")
    print(f"commercial-flagged: {props['is_commercial'].sum():,}  carspace: {props['is_carspace'].sum():,}")
    print(f"floor_est coverage: {props['floor_est'].notna().mean():.1%}")
    print(f"clean unit sales: {len(sales):,}  ({sales['sold_date'].min().date()} to {sales['sold_date'].max().date()})")
    print(sales["sold_price"].describe().round(0).to_string())
