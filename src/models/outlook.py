"""ValuIQ value outlook (1-5 years), built only from our own sales history up to 31 Aug 2026.

Central path: the repeat-sales index's trailing 10-year compound growth, adjusted per suburb by
how that suburb's repeat-sale growth compares with the city's (shrunk towards the city for thin
suburbs). Range: calibrated from a backtest that re-runs the same rule at every quarter from 2005
using only the index history available then; the band at each horizon is the 68th percentile of
past absolute log errors, so it would have captured about two-thirds of outcomes historically.
"""
import numpy as np
import pandas as pd

from src.models.price_index import repeat_pairs

TRAILING_YEARS = 10
SUBURB_SHRINK_PAIRS = 200  # pseudo-count pulling suburb adjustments towards zero


def city_growth(index, end=None):
    """Trailing 10-year log growth per year, and the sd of annual log growth, using index up to `end`."""
    ix = index if end is None else index[index.index <= end]
    q = TRAILING_YEARS * 4
    g = (ix.iloc[-1] - ix.iloc[-1 - q]) / TRAILING_YEARS
    sd = ix.diff(4).iloc[-q:].std()
    return float(g), float(sd)


def suburb_adjustments(sales, cutoff):
    """Log-growth-per-year premium of each suburb over the city, from repeat pairs sold in the
    trailing window before cutoff, shrunk towards 0."""
    s = sales[sales["sold_date"] < cutoff]
    pairs = repeat_pairs(s)
    pairs = pairs[pairs["t1"] >= pd.Timestamp(cutoff) - pd.DateOffset(years=TRAILING_YEARS)]
    pairs = pairs.merge(s[["gnaf_pid", "api_suburb"]].drop_duplicates("gnaf_pid"), on="gnaf_pid")
    years = (pairs["t1"] - pairs["t0"]).dt.days / 365.25
    pairs["g"] = (pairs["p1"] - pairs["p0"]) / years
    city = pairs["g"].median()
    by = pairs.groupby("api_suburb")["g"].agg(["median", "size"])
    adj = (by["median"] - city) * by["size"] / (by["size"] + SUBURB_SHRINK_PAIRS)
    return {k: float(v) for k, v in adj.items()}, {k: int(v) for k, v in by["size"].items()}


def backtest(index, horizons=(1, 2, 3, 4, 5), start="2005Q1"):
    """Re-run the city rule at each quarter; compare with realised index growth."""
    rows = []
    periods = index.index[index.index >= pd.Period(start, "Q")]
    for p in periods:
        hist = index[index.index <= p]
        if len(hist) <= TRAILING_YEARS * 4:
            continue
        g, sd = city_growth(index, end=p)
        for h in horizons:
            fut = p + 4 * h
            if fut not in index.index:
                continue
            actual = index[fut] - index[p]
            rows.append({"h": h, "err": g * h - actual, "inside_sd": abs(g * h - actual) <= sd * np.sqrt(h)})
    df = pd.DataFrame(rows)
    return {int(h): {"n": int(len(d)),
                     "median_abs_error_pct": float(np.median(np.abs(np.expm1(d["err"]))) * 100),
                     "sd_band_coverage_pct": float(d["inside_sd"].mean() * 100),
                     "band_log": float(np.quantile(np.abs(d["err"]), 0.68))}
            for h, d in df.groupby("h")}
