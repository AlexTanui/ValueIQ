"""Chronological validation: information cutoff SPLIT_DATE, validate on unit
sales from SPLIT_DATE to the valuation date.

Mirrors the competition: features and index use only sales before the cutoff,
and the target sales happen 0-2 months after it.
"""
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from src.features.feature_engineering import FEATURES, build_features
from src.models.price_index import build_index, index_at
from src.preprocessing.clean_data import VALUATION_DATE, load_properties, load_sales
from src.validation.evaluate import metrics

SPLIT_DATE = pd.Timestamp("2026-07-01")
TRAIN_FROM = pd.Timestamp("2010-01-01")
OUT_DIR = Path(__file__).resolve().parents[2] / "outputs"

LGB_PARAMS = dict(objective="huber", alpha=0.15, learning_rate=0.03, num_leaves=63,
                  min_child_samples=30, feature_fraction=0.8, bagging_fraction=0.8,
                  bagging_freq=1, lambda_l2=1.0, verbose=-1, seed=7)
N_ROUNDS = 1500


def training_frame(sales, cutoff, index):
    """Every sale before cutoff, featurised with information strictly before its own date."""
    train = sales[(sales["sold_date"] >= TRAIN_FROM) & (sales["sold_date"] < cutoff)].copy()
    train["info_date"] = train["sold_date"]
    X = build_features(train, sales[sales["sold_date"] < cutoff], index)
    X["target"] = X["log_price"] - index_at(index, X["sold_date"])
    return X


def fit_lgb(X):
    w = np.where(X["sold_date"] >= X["sold_date"].max() - pd.Timedelta(days=3 * 365), 2.0, 1.0)
    ds = lgb.Dataset(X[FEATURES], X["target"], weight=w, categorical_feature="auto")
    return lgb.train(LGB_PARAMS, ds, num_boost_round=N_ROUNDS)


def baseline_predictions(V, level):
    """Simple fallback chains in adjusted-log space, plus the index level."""
    sub_bed = V["subbed_mean"].fillna(V["sub_mean"])
    bld_bed = V["bldbed_mean"].where(V["bldbed_n"] >= 2).fillna(sub_bed)
    last_sale = V["own_last_adj"].fillna(bld_bed)
    return {
        "suburb_bedroom_median": np.exp(sub_bed + level),
        "building_bedroom_mean": np.exp(bld_bed + level),
        "last_sale_indexed": np.exp(last_sale + level),
    }


def main():
    props = load_properties()
    sales = load_sales(props)
    index = build_index(sales, SPLIT_DATE)
    level = index.iloc[-1]

    X = training_frame(sales, SPLIT_DATE, index)
    val = sales[(sales["sold_date"] >= SPLIT_DATE) & (sales["sold_date"] <= VALUATION_DATE)].copy()
    val["info_date"] = SPLIT_DATE
    V = build_features(val, sales[sales["sold_date"] < SPLIT_DATE], index)

    model = fit_lgb(X)
    preds = baseline_predictions(V, level)
    preds["lightgbm"] = np.exp(model.predict(V[FEATURES]) + level)

    actual = V["sold_price"].to_numpy()
    under = actual < 1_200_000
    results = {}
    for name, p in preds.items():
        results[name] = {"all": metrics(actual, p), "under_1.2m": metrics(actual[under], np.asarray(p)[under])}
        r, u = results[name]["all"], results[name]["under_1.2m"]
        print(f"{name:24s} within10 all={r['within_10pct']:.1%} (<1.2M {u['within_10pct']:.1%})  "
              f"MdAE={u['median_abs_error']:,.0f}  R2={r['r2']:.3f}")

    print(f"\nsplit={SPLIT_DATE.date()} train={len(X):,} validation={len(V):,} (<1.2M {under.sum()})")
    imp = pd.Series(model.feature_importance("gain"), index=FEATURES).sort_values(ascending=False)
    print(imp.head(15).round(0).to_string())

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "validation_results.json").write_text(json.dumps(
        {"split_date": str(SPLIT_DATE.date()), "n_train": len(X), "n_validation": len(V),
         "n_validation_under_1.2m": int(under.sum()), "results": results}, indent=2))
    V.assign(**{f"pred_{k}": v for k, v in preds.items()}).to_parquet(OUT_DIR / "validation_predictions.parquet")


if __name__ == "__main__":
    main()
