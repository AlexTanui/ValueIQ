"""Export the data the ValuIQ web app (app/) reads, into app/public/data/ (git-ignored).

Files:
  summary.json     headline metrics, model comparison, price index
  buildings.json   one row per building: location, median value, units
  addresses.json   one row per supplied address: value and evidence
  comps.json       recent sales per building (supplied prices -- local only)
  validation.json  Jul-Aug 2026 holdout errors as percentages

comps.json contains supplied sale prices, so the folder must never be committed.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.models.price_index import build_index, index_at
from src.predict import INFO_CUTOFF
from src.preprocessing.clean_data import load_properties, load_sales
from src.validation.run_validation import FOLDS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
APP_DATA = ROOT / "app" / "public" / "data"
COMPS_PER_BUILDING = 10
MODEL_LABELS = {
    "suburb_bedroom_median": "Suburb × bedroom median",
    "building_bedroom_mean": "Building × bedroom mean",
    "last_sale_indexed": "Last sale + repeat-sales index",
    "lightgbm_seed_avg": "ValuIQ LightGBM",
}
BENCHMARKS = [("Organiser: existing AVM", 34 / 227), ("Organiser: suburb × bedroom median", 86 / 227),
              ("Organiser: last sale + citywide index", 109 / 227)]


def _num(x, nd=None):
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x):
        return None
    return round(float(x), nd) if nd else int(round(float(x)))


def _dump(name, obj):
    (APP_DATA / name).write_text(json.dumps(obj, separators=(",", ":")))


def main():
    APP_DATA.mkdir(parents=True, exist_ok=True)
    props = load_properties()
    sales = load_sales(props)
    index = build_index(sales, INFO_CUTOFF)
    level = index.iloc[-1]
    P = pd.read_parquet(OUT / "all_predictions.parquet")
    P["address"] = props.set_index("gnaf_pid").reindex(P["gnaf_pid"])["address"].to_numpy()
    dollars = lambda adj: np.exp(np.asarray(adj, dtype=float) + level)

    # Buildings
    B = P.groupby("building_key").agg(
        lat=("lat", "median"), lng=("lng", "median"), value=("value", "median"),
        units=("gnaf_pid", "size"), suburb=("api_suburb", "first"),
        commercial=("is_commercial", "mean"), floors=("floor_est", "max"),
        sales=("bld_n", "max")).reset_index()
    B["street"] = B["building_key"].str.split("|").str[0].str.title()
    bidx = {k: i for i, k in enumerate(B["building_key"])}
    _dump("buildings.json", [[r.street, r.suburb, round(r.lat, 6), round(r.lng, 6), _num(r.value, -3),
                              int(r.units), _num(r.floors), int(r.sales or 0), round(float(r.commercial), 2)]
                             for r in B.itertuples()])

    # Addresses with evidence in Aug-2026 dollars
    own, bldbed = dollars(P["own_last_adj"]), dollars(P["bldbed_mean"])
    nbr = dollars(P["nbr_bed_mean"].fillna(P["nbr_mean"]))
    _dump("addresses.json", [
        [r.gnaf_pid, r.address, r.api_suburb, _num(r.value), _num(r.bedrooms), _num(r.bathrooms),
         _num(r.car_spaces), bidx[r.building_key], round(r.lat, 6), round(r.lng, 6),
         _num(own[i], -3), _num(r.own_years_since, 1), _num(bldbed[i], -3), int(r.bldbed_n),
         _num(nbr[i], -3), _num(r.floor_est), int(bool(r.is_commercial))]
        for i, r in enumerate(P.itertuples())])

    # Recent sales per building (local only)
    s = sales.copy()
    s["today"] = np.exp(s["log_price"] - index_at(index, s["sold_date"]) + level)
    s = s.sort_values("sold_date").groupby("building_key").tail(COMPS_PER_BUILDING)
    addr = props.set_index("gnaf_pid")["address"]
    comps = {}
    for b, g in s.groupby("building_key"):
        comps[bidx[b]] = [[addr.get(x, "").split(",")[0], d.strftime("%b %Y"), int(p), _num(t, -3), _num(bd)]
                          for x, d, p, t, bd in zip(g["gnaf_pid"], g["sold_date"], g["sold_price"],
                                                     g["today"], g["bedrooms"])][::-1]
    _dump("comps.json", comps)

    # Validation errors (percent only)
    V = pd.read_parquet(OUT / "validation_predictions.parquet")
    V = V[V["fold"] == FOLDS[-1][0]]
    err = (V["pred_lightgbm_seed_avg"] / V["sold_price"] - 1) * 100
    _dump("validation.json", [[round(a, 6), round(b, 6), round(float(e), 1), _num(bd)]
                              for a, b, e, bd in zip(V["lat"], V["lng"], err, V["bedrooms"])])

    # Summary
    S = pd.read_csv(OUT / "validation_summary.csv")
    last = S[S["fold"] == FOLDS[-1][0]].set_index("model")
    per_fold = S.pivot(index="model", columns="fold", values="u12_within_10pct")
    hl = last.loc["lightgbm_seed_avg"]
    idx = np.exp(index - level)
    idx = idx[idx.index >= pd.Period("2005Q1", "Q")]
    comparison = [{"label": MODEL_LABELS[m], "value": float(last.loc[m, "u12_within_10pct"]),
                   "ours": m == "lightgbm_seed_avg"} for m in MODEL_LABELS]
    comparison += [{"label": l, "value": v, "ours": False, "organiser": True} for l, v in BENCHMARKS]
    _dump("summary.json", {
        "headline": {"within10": float(hl["u12_within_10pct"]), "mdae": float(hl["u12_median_abs_error"]),
                     "r2": float(hl["all_r2"]), "n_val": int(hl["n_val"]), "n_val_u12": int(hl["n_val_under_1.2m"]),
                     "fold_mean": float(per_fold.loc["lightgbm_seed_avg"].mean()), "n_addresses": len(P),
                     "n_sales": len(sales), "missing": int(hl["u12_missing"])},
        "comparison": sorted(comparison, key=lambda d: -d["value"]),
        "index": {"labels": [str(p) for p in idx.index], "values": [round(float(x), 4) for x in idx]},
        "value_breaks": [int(round(x, -3)) for x in np.quantile(B.loc[B["commercial"] < 0.5, "value"],
                                                                [1 / 7 * i for i in range(1, 7)])],
    })
    sizes = {f.name: f"{f.stat().st_size / 1e6:.1f} MB" for f in APP_DATA.glob("*.json")}
    print(f"exported to app/public/data: {sizes}")


if __name__ == "__main__":
    main()
