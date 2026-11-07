"""Chronological validation over rolling 2-month folds.

For each fold the information cutoff is the fold start: the index, training
set and features use only sales before it, and the model is scored on unit
sales in the following two months. This mirrors the competition, where values
at 31 August 2026 are scored on sales 0-2 months later. The final fold
(cutoff 1 July 2026, scored on July-August) is the headline result.
"""
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from src.features.feature_engineering import FEATURES, build_features
from src.models.price_index import build_index, index_at
from src.preprocessing.clean_data import load_properties, load_sales
from src.validation.evaluate import metrics

FOLDS = [("2026-03-01", "2026-04-30"), ("2026-05-01", "2026-06-30"), ("2026-07-01", "2026-08-31")]
TRAIN_FROM = pd.Timestamp("2010-01-01")
OUT_DIR = Path(__file__).resolve().parents[2] / "outputs"

LGB_PARAMS = dict(objective="huber", alpha=0.15, learning_rate=0.03, num_leaves=63,
                  min_child_samples=30, feature_fraction=0.8, bagging_fraction=0.8,
                  bagging_freq=1, lambda_l2=1.0, verbose=-1)
N_ROUNDS = 1500
SEEDS = [7, 11, 23, 42, 101]


def training_frame(sales, cutoff, index):
    """Every sale before cutoff, featurised with information strictly before its own date."""
    train = sales[(sales["sold_date"] >= TRAIN_FROM) & (sales["sold_date"] < cutoff)].copy()
    train["info_date"] = train["sold_date"]
    X = build_features(train, sales[sales["sold_date"] < cutoff], index)
    X["target"] = X["log_price"] - index_at(index, X["sold_date"])
    return X


def _recency_weight(X):
    return np.where(X["sold_date"] >= X["sold_date"].max() - pd.Timedelta(days=3 * 365), 2.0, 1.0)


def fit_lgb(X, seeds=SEEDS):
    """One LightGBM model per seed (seed varies bagging and feature sampling)."""
    ds = lgb.Dataset(X[FEATURES], X["target"], weight=_recency_weight(X), categorical_feature="auto",
                     free_raw_data=False)
    return [lgb.train({**LGB_PARAMS, "seed": s}, ds, num_boost_round=N_ROUNDS) for s in seeds]


def predict_adj(models, X):
    """LightGBM predictions in adjusted-log space: first seed alone, and the seed average.

    CatBoost and a 50/50 blend were tested on the same folds and were worse
    and unstable (mean within-10% 38.8% and 45.8% vs 63.5%), so they were dropped.
    """
    preds = np.column_stack([m.predict(X[FEATURES]) for m in models])
    return {"lightgbm": preds[:, 0], "lightgbm_seed_avg": preds.mean(axis=1)}


def baseline_adj(V):
    """Simple fallback chains in adjusted-log space."""
    sub_bed = V["subbed_mean"].fillna(V["sub_mean"])
    bld_bed = V["bldbed_mean"].where(V["bldbed_n"] >= 2).fillna(sub_bed)
    return {
        "suburb_bedroom_median": sub_bed.to_numpy(),
        "building_bedroom_mean": bld_bed.to_numpy(),
        "last_sale_indexed": V["own_last_adj"].fillna(bld_bed).to_numpy(),
    }


def validation_targets(sales, props, cutoff, end):
    """Confirmed flat sales in the window, with the unit attributes we would
    actually have at prediction time (the supplied input file), not the sale's."""
    val = sales[(sales["sold_date"] >= cutoff) & (sales["sold_date"] <= end)
                & sales["source"].eq("flat_sales")].copy()
    attrs = props.set_index("gnaf_pid")[["bedrooms", "bathrooms", "car_spaces"]]
    val[attrs.columns] = attrs.reindex(val["gnaf_pid"]).to_numpy()
    val["info_date"] = cutoff
    return val


def run_fold(sales, props, start, end):
    cutoff, end = pd.Timestamp(start), pd.Timestamp(end)
    index = build_index(sales, cutoff)
    level = index.iloc[-1]
    history = sales[sales["sold_date"] < cutoff]

    X = training_frame(sales, cutoff, index)
    V = build_features(validation_targets(sales, props, cutoff, end), history, index)

    models = fit_lgb(X)
    adj = {**baseline_adj(V), **predict_adj(models, V)}
    preds = {k: np.exp(v + level) for k, v in adj.items()}
    return X, V, preds, models


def main():
    props = load_properties()
    sales = load_sales(props)
    summary, frames = [], []
    for start, end in FOLDS:
        X, V, preds, models = run_fold(sales, props, start, end)
        actual = V["sold_price"].to_numpy()
        under = actual < 1_200_000
        for name, p in preds.items():
            summary.append({"fold": start, "model": name, "n_train": len(X), "n_val": len(V),
                            "n_val_under_1.2m": int(under.sum()),
                            **{f"all_{k}": v for k, v in metrics(actual, p).items()},
                            **{f"u12_{k}": v for k, v in metrics(actual[under], p[under]).items()}})
        frames.append(V.assign(fold=start, **{f"pred_{k}": v for k, v in preds.items()}))
        print(f"fold {start}: train={len(X):,} val={len(V):,} (<1.2M {under.sum()})", flush=True)

    S = pd.DataFrame(summary)
    table = S.pivot(index="model", columns="fold", values="u12_within_10pct")
    table["mean"] = table.mean(axis=1)
    print("\nWithin 10% (sales under $1.2M) by fold:")
    print((table * 100).round(1).sort_values("mean").to_string())
    last = S[S["fold"] == FOLDS[-1][0]].set_index("model")
    print(f"\nHeadline fold {FOLDS[-1][0]} (sales under $1.2M):")
    print(last[["u12_within_10pct", "u12_median_abs_error", "u12_mae", "u12_rmse", "u12_r2",
                "all_within_10pct", "all_r2"]].round(3).to_string())

    imp = pd.Series(models[0].feature_importance("gain"), index=FEATURES).sort_values(ascending=False)
    OUT_DIR.mkdir(exist_ok=True)
    S.to_csv(OUT_DIR / "validation_summary.csv", index=False)
    imp.to_csv(OUT_DIR / "feature_importance.csv", header=["gain"])
    pd.concat(frames).to_parquet(OUT_DIR / "validation_predictions.parquet")
    (OUT_DIR / "validation_results.json").write_text(json.dumps(
        {"folds": FOLDS, "headline": last.reset_index().to_dict(orient="records")}, indent=2, default=float))


if __name__ == "__main__":
    main()
