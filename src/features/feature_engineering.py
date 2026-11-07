"""Point-in-time features: every statistic uses only sales dated strictly
before each row's `info_date`.

Sale prices are first converted to index-adjusted log prices
(adj = log_price - log_index(sale quarter)), so sales from different years are
comparable. The model predicts adj; the index level at the valuation date is
added back afterwards.
"""
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from src.features.location import LOCATION_FEATURES
from src.models.price_index import index_at

GRID_DEG = 0.0025  # ~250 m cells
EARTH_M = 6_371_000
NBR_WINDOW_YEARS = 2
NBR_K = 20
NBR_K_BED = 10
NBR_SOFTEN_M = 30  # weight = 1 / (distance + NBR_SOFTEN_M)

GROUP_KEYS = {
    "own": ["gnaf_pid"],
    "bld": ["building_key"],
    "bldbed": ["building_key", "bed_key"],
    "mb": ["mb"],
    "cell": ["cell"],
    "subbed": ["api_suburb", "bed_key"],
    "sub": ["api_suburb"],
}

CATEGORICAL = ["api_suburb", "block_type", "addr_prefix"]
BLOCK_FEATURES = ["mb_homes_2021", "mb_people_per_home_2021", "mb_new_homes", "mb_new_home_share"]
NEIGHBOUR_FEATURES = ["nbr_mean", "nbr_dist_m", "nbr_bed_mean", "nbr_bed_dist_m"]
NUMERIC = [
    "bedrooms", "bathrooms", "car_spaces", "flats_in_building", "floor_est", "unit_no",
    "lat", "lng", "dist_cbd_km", "is_commercial", "is_carspace", "bld_age_years",
    "own_last_adj", "own_years_since", "bld_last_adj", "bld_years_since",
] + LOCATION_FEATURES + BLOCK_FEATURES + NEIGHBOUR_FEATURES
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


def _knn(events, targets, k, prefix):
    """Distance-weighted mean adj of the k nearest sales in the NBR_WINDOW_YEARS
    before each target's info month, excluding the target's own flat."""
    out = np.full((len(targets), 2), np.nan)
    months = targets["info_date"].dt.to_period("M")
    ev_time = events["sold_date"].to_numpy()
    for month, idx in targets.groupby(months).indices.items():
        start = month.to_timestamp()  # events strictly before the info month: leakage-free
        win = events[(ev_time < start) & (ev_time >= start - pd.DateOffset(years=NBR_WINDOW_YEARS))]
        if len(win) < 3:
            continue
        tree = BallTree(np.radians(win[["lat", "lng"]].to_numpy()), metric="haversine")
        kk = min(k + 1, len(win))
        t = targets.iloc[idx]
        dist, ind = tree.query(np.radians(t[["lat", "lng"]].to_numpy()), k=kk)
        dist = dist * EARTH_M
        same = win["gnaf_pid"].to_numpy()[ind] == t["gnaf_pid"].to_numpy()[:, None]
        w = np.where(same, 0.0, 1.0 / (dist + NBR_SOFTEN_M))
        adj = win["adj"].to_numpy()[ind]
        out[idx, 0] = (w * adj).sum(1) / w.sum(1)
        out[idx, 1] = np.median(np.where(same, np.nan, dist), axis=1)
    return pd.DataFrame(out, columns=[f"{prefix}_mean", f"{prefix}_dist_m"], index=targets.index)


def neighbour_features(events, targets):
    """Nearby recent sales: any bedroom count, and the same bedroom count."""
    allk = _knn(events, targets, NBR_K, "nbr")
    bed = pd.DataFrame(np.nan, index=targets.index, columns=["nbr_bed_mean", "nbr_bed_dist_m"])
    for b in range(0, 5):
        tmask = targets["bed_key"].eq(b).to_numpy()
        if tmask.any():
            r = _knn(events[events["bed_key"].eq(b)], targets[tmask], NBR_K_BED, "nbr_bed")
            bed.loc[r.index, r.columns] = r.to_numpy()
    return pd.concat([allk, bed], axis=1)


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
    parts.append(neighbour_features(events, targets))
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
