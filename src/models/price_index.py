"""Quarterly repeat-sales (Bailey-Muth-Nourse) price index for City of Sydney units.

Built only from sales strictly before `cutoff`, so a validation or final run
never sees prices from after its information date.
"""
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import lsqr

MIN_HOLD_DAYS = 180
MAX_ABS_ANNUAL_LOG_RETURN = 0.5


def repeat_pairs(sales):
    """Consecutive sales of the same address as (log_p0, t0, log_p1, t1)."""
    s = sales.sort_values(["gnaf_pid", "sold_date"])
    prev = s.groupby("gnaf_pid")[["log_price", "sold_date"]].shift(1)
    pairs = pd.DataFrame({
        "gnaf_pid": s["gnaf_pid"], "group": s.get("index_group"),
        "p0": prev["log_price"], "t0": prev["sold_date"],
        "p1": s["log_price"], "t1": s["sold_date"],
    }).dropna(subset=["p0"])
    years = (pairs["t1"] - pairs["t0"]).dt.days / 365.25
    ok = (years * 365.25 >= MIN_HOLD_DAYS) & (
        ((pairs["p1"] - pairs["p0"]) / years).abs() <= MAX_ABS_ANNUAL_LOG_RETURN)
    return pairs[ok]


def build_index(sales, cutoff, start="1995-01-01", ridge=2.0):
    """Return a Series of log index levels by quarter (PeriodIndex), 0 at the first quarter.

    A small ridge penalty on quarter-to-quarter changes keeps thin quarters smooth.
    """
    s = sales[(sales["sold_date"] < pd.Timestamp(cutoff)) & (sales["sold_date"] >= pd.Timestamp(start))]
    pairs = repeat_pairs(s)
    q0, q1 = pairs["t0"].dt.to_period("Q"), pairs["t1"].dt.to_period("Q")
    periods = pd.period_range(pd.Period(start, "Q"), pd.Timestamp(cutoff).to_period("Q"), freq="Q")
    pos = {p: i for i, p in enumerate(periods)}
    i0, i1 = q0.map(pos).to_numpy(), q1.map(pos).to_numpy()
    keep = i0 != i1
    i0, i1, y = i0[keep], i1[keep], (pairs["p1"] - pairs["p0"]).to_numpy()[keep]

    # Unknowns are levels for periods 1..T-1 (period 0 fixed at 0).
    n, T = len(y), len(periods)
    rows = np.r_[np.arange(n), np.arange(n)]
    cols = np.r_[i1, i0]
    vals = np.r_[np.ones(n), -np.ones(n)]
    m = cols > 0
    A = coo_matrix((vals[m], (rows[m], cols[m] - 1)), shape=(n, T - 1))

    # Ridge on first differences: level[t] - level[t-1] ~ 0
    d_rows = np.r_[np.arange(T - 1), np.arange(1, T - 1)]
    d_cols = np.r_[np.arange(T - 1), np.arange(0, T - 2)]
    d_vals = np.r_[np.ones(T - 1), -np.ones(T - 2)] * ridge
    D = coo_matrix((d_vals, (d_rows, d_cols)), shape=(T - 1, T - 1))

    from scipy.sparse import vstack
    sol = lsqr(vstack([A, D]).tocsr(), np.r_[y, np.zeros(T - 1)])[0]
    return pd.Series(np.r_[0.0, sol], index=periods, name="log_index")


def index_at(index, dates):
    """Log index level for each date; dates beyond the index use the last level."""
    q = pd.DatetimeIndex(dates).to_period("Q")
    q = q.where(q <= index.index[-1], index.index[-1])
    q = q.where(q >= index.index[0], index.index[0])
    return index.reindex(q).to_numpy()
