"""Build report.html from the pipeline outputs.

Only derived, aggregated material is embedded: building-level predicted
values, validation errors as percentages (no sale prices), the price index and
metrics. No raw API records or supplied-file rows go into the page.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.models.price_index import build_index
from src.predict import INFO_CUTOFF
from src.preprocessing.clean_data import load_properties, load_sales
from src.validation.run_validation import FOLDS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
TEMPLATE = Path(__file__).with_name("template.html")

BENCHMARKS = [  # organiser results on 227 private sales under $1.2M (task brief)
    ("Microburbs existing AVM (organiser)", 34 / 227),
    ("Suburb × bedroom median (organiser)", 86 / 227),
    ("Last sale + citywide index (organiser)", 109 / 227),
]
MODEL_LABELS = {
    "suburb_bedroom_median": "Suburb × bedroom median (ours)",
    "building_bedroom_mean": "Building × bedroom mean (ours)",
    "last_sale_indexed": "Last sale + repeat-sales index (ours)",
    "lightgbm": "LightGBM, single seed (ours)",
    "lightgbm_seed_avg": "ValuIQ LightGBM, 5-seed average",
}


def building_points(P):
    u = P[~P["is_commercial"].astype(bool)]
    b = u.groupby("building_key").agg(
        lat=("lat", "median"), lng=("lng", "median"), value=("value", "median"),
        n=("gnaf_pid", "size"), suburb=("api_suburb", "first"),
        age=("bld_age_years", "median"),
        floors=("floor_est", "max"))
    return [[round(r.lat, 5), round(r.lng, 5), int(round(r.value, -3)), int(r.n), r.suburb,
             None if pd.isna(r.age) else int(r.age), None if pd.isna(r.floors) else int(r.floors)]
            for r in b.itertuples()]


def validation_points(V):
    v = V[V["fold"] == FOLDS[-1][0]]
    err = v["pred_lightgbm_seed_avg"] / v["sold_price"] - 1
    return [[round(a, 5), round(b, 5), round(float(e) * 100, 1),
             None if pd.isna(bd) else int(bd)]
            for a, b, e, bd in zip(v["lat"], v["lng"], err, v["bedrooms"])]


def main():
    props = load_properties()
    sales = load_sales(props)
    index = build_index(sales, INFO_CUTOFF)
    idx = np.exp(index - index.iloc[-1])
    idx = idx[idx.index >= pd.Period("2005Q1", "Q")]

    P = pd.read_parquet(OUT / "all_predictions.parquet")
    V = pd.read_parquet(OUT / "validation_predictions.parquet")
    S = pd.read_csv(OUT / "validation_summary.csv")
    imp = pd.read_csv(OUT / "feature_importance.csv", index_col=0)["gain"]
    imp = (imp / imp.sum()).sort_values(ascending=False).head(12)

    last = S[S["fold"] == FOLDS[-1][0]].set_index("model")
    per_fold = S.pivot(index="model", columns="fold", values="u12_within_10pct")
    comparison = [{"label": MODEL_LABELS[m], "value": float(last.loc[m, "u12_within_10pct"]),
                   "ours": m == "lightgbm_seed_avg"} for m in MODEL_LABELS]
    comparison += [{"label": l, "value": v, "ours": False, "organiser": True} for l, v in BENCHMARKS]
    comparison.sort(key=lambda d: d["value"])

    metrics_rows = []
    for m in MODEL_LABELS:
        r = last.loc[m]
        metrics_rows.append({
            "model": MODEL_LABELS[m],
            "folds": [float(per_fold.loc[m, f]) for f, _ in FOLDS],
            "within": float(r["u12_within_10pct"]), "mdae": float(r["u12_median_abs_error"]),
            "mae": float(r["u12_mae"]), "rmse": float(r["u12_rmse"]),
            "r2_u12": float(r["u12_r2"]), "r2_all": float(r["all_r2"]),
            "within_all": float(r["all_within_10pct"]), "missing": int(r["u12_missing"]),
        })

    units = P[~P["is_commercial"].astype(bool)]
    data = {
        "buildings": building_points(P),
        "validation": validation_points(V),
        "index": {"labels": [str(p) for p in idx.index], "values": [round(float(x), 4) for x in idx]},
        "comparison": comparison,
        "importance": [{"label": k, "value": float(v)} for k, v in imp.items()],
        "metrics": metrics_rows,
        "folds": [f"{a} to {b}" for a, b in FOLDS],
        "facts": {
            "n_props": len(P), "n_units": len(units), "n_buildings": int(units["building_key"].nunique()),
            "n_sales_clean": len(sales), "n_train": int(last.loc["lightgbm_seed_avg", "n_train"]),
            "n_val": int(last.loc["lightgbm_seed_avg", "n_val"]),
            "n_val_u12": int(last.loc["lightgbm_seed_avg", "n_val_under_1.2m"]),
            "headline": float(last.loc["lightgbm_seed_avg", "u12_within_10pct"]),
            "mdae": float(last.loc["lightgbm_seed_avg", "u12_median_abs_error"]),
            "r2_all": float(last.loc["lightgbm_seed_avg", "all_r2"]),
            "best_benchmark": 109 / 227,
            "fold_mean": float(per_fold.loc["lightgbm_seed_avg"].mean()),
            "unit_median": float(units["value"].median()),
        },
    }
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    (ROOT / "report.html").write_text(html, encoding="utf-8")
    print(f"report.html written ({len(html) / 1e6:.1f} MB, {len(data['buildings']):,} buildings, "
          f"{len(data['validation'])} validation points)")


if __name__ == "__main__":
    main()
