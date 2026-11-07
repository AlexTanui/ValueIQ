"""Point-in-time features: every statistic uses only sales dated strictly
before each row's `info_date`.

Sale prices are first converted to index-adjusted log prices
(adj = log_price - log_index(sale quarter)), so sales from different years are
comparable. The model predicts adj; the index level at the valuation date is
added back afterwards.
"""
import numpy as np
import pandas as pd

from src.models.price_index import index_at

GRID_DEG = 0.0025  # ~250 m cells

GROUP_KEYS = {
    "own": ["gnaf_pid"],
    "bld": ["building_key"],
    "bldbed": ["building_key", "bed_key"],
    "mb": ["mb"],
    "cell": ["cell"],
    "subbed": ["api_suburb", "bed_key"],
    "sub": ["api_suburb"],
}

CATEGORICAL = ["api_suburb", "dwelling_type", "addr_prefix"]
NUMERIC = [
    "bedrooms", "bathrooms", "car_spaces", "flats_in_building", "floor_est", "unit_no",
    "lat", "lng", "dist_cbd_km", "is_commercial", "is_carspace", "bld_age_years",
    "own_last_adj", "own_years_since", "bld_last_adj", "bld_years_since",
]
for _g in GROUP_KEYS:
    NUMERIC += [f"{_g}_mean", f"{_g}_n"]
FEATURES = NUMERIC + CATEGORICAL


def add_keys(df):
    df = df.copy()
    df["bed_key"] = df["bedrooms"].fillna(-1).clip(upper=4).astype(int)
    df["cell"] = ((df["lat"] / GRID_DEG).round().astype(int).astype(str) + "_"
                  + (df["lng"] / GRID_DEG).round().astype(int).astype(str))
    for c in ["gnaf_pid", "building_key", "mb", "api_suburb", "cell"]:
        df[c] = df[c].astype(str).astype("string")
    return df


def _prior_mean(events, targets, keys, name):
    """Mean and count of events.adj per key, using only events before targets.info_date."""
    agg = events.groupby(keys + ["sold_date"])["adj"].agg(["sum", "count"]).reset_index()
    agg = agg.sort_values("sold_date")
    agg[keys] = agg[keys].astype("string")
    agg[["csum", "ccount"]] = agg.groupby(keys)[["sum", "count"]].cumsum()
    t = targets[keys + ["info_date", "_row"]].sort_values("info_date")
    t[keys] = t[keys].astype("string")
    m = pd.merge_asof(t, agg[keys + ["sold_date", "csum", "ccount"]], left_on="info_date",
                      right_on="sold_date", by=keys, allow_exact_matches=False)
    m = m.set_index("_row").reindex(targets["_row"])
    return pd.DataFrame({f"{name}_mean": (m["csum"] / m["ccount"]).to_numpy(),
                         f"{name}_n": m["ccount"].fillna(0).to_numpy()}, index=targets.index)


def _prior_last(events, targets, keys, name):
    """Most recent prior adj value and years since it."""
    e = events[keys + ["sold_date", "adj"]].sort_values("sold_date")
    t = targets[keys + ["info_date", "_row"]].sort_values("info_date")
    e[keys] = e[keys].astype("string")
    t[keys] = t[keys].astype("string")
    m = pd.merge_asof(t, e, left_on="info_date", right_on="sold_date", by=keys,
                      allow_exact_matches=False).set_index("_row").reindex(targets["_row"])
    years = (targets["info_date"].to_numpy() - m["sold_date"].to_numpy()) / np.timedelta64(1, "D") / 365.25
    return pd.DataFrame({f"{name}_last_adj": m["adj"].to_numpy(),
                         f"{name}_years_since": years}, index=targets.index)


def build_features(targets, history, index):
    """targets: rows to featurise, with `info_date`; history: clean sales usable as evidence."""
    targets = add_keys(targets).reset_index(drop=True)
    targets["_row"] = np.arange(len(targets))
    events = add_keys(history)
    events["adj"] = events["log_price"] - index_at(index, events["sold_date"])

    parts = [targets]
    for name, keys in GROUP_KEYS.items():
        parts.append(_prior_mean(events, targets, keys, name))
    parts.append(_prior_last(events, targets, ["gnaf_pid"], "own"))
    parts.append(_prior_last(events, targets, ["building_key"], "bld"))
    out = pd.concat(parts, axis=1)

    first = events.groupby("building_key")["sold_date"].min().rename("bld_first_sale")
    out = out.merge(first, left_on="building_key", right_index=True, how="left")
    age = (out["info_date"] - out["bld_first_sale"]).dt.days / 365.25
    out["bld_age_years"] = age.where(age > 0)

    for c in CATEGORICAL:
        out[c] = out[c].fillna("NA").astype("category")
    for c in ["is_commercial", "is_carspace"]:
        out[c] = out[c].astype(float)
    return out
