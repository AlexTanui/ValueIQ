"""Value every address at 31 August 2026 and write the submission CSV.

Information cutoff: sales dated on or before 31 August 2026 only. The index,
training set and features all come from that history.

Usage:
  python -m src.predict                        # values every API address
  python -m src.predict data/flats-city-of-sydney.csv   # restrict to the official ID list
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.feature_engineering import FEATURES, build_features
from src.models.price_index import build_index
from src.preprocessing.clean_data import VALUATION_DATE, load_properties, load_sales
from src.validation.run_validation import fit_lgb, training_frame

ROOT = Path(__file__).resolve().parents[1]
TEAM = "valuiq"
INFO_CUTOFF = VALUATION_DATE + pd.Timedelta(days=1)  # sales strictly before this are usable


def main(input_csv=None):
    units = load_properties(units_only=True)
    sales = load_sales(units)
    index = build_index(sales, INFO_CUTOFF)
    level = index.iloc[-1]

    X = training_frame(sales, INFO_CUTOFF, index)
    model = fit_lgb(X)

    props = load_properties(units_only=False)
    props["info_date"] = INFO_CUTOFF
    P = build_features(props, sales, index)
    value = np.exp(model.predict(P[FEATURES]) + level)
    out = pd.DataFrame({"gnaf_id": P["gnaf_pid"].astype(str), "value": value})

    if input_csv:
        ids = pd.read_csv(input_csv, usecols=["gnaf_id"], dtype=str)
        out = ids.merge(out, on="gnaf_id", how="left")
        missing = out["value"].isna().sum()
        if missing:
            print(f"{missing:,} official IDs not in API pull; using median unit value fallback")
            out["value"] = out["value"].fillna(np.median(value[P["property_type"].eq("Unit")]))

    out["value"] = out["value"].round().astype("int64")
    path = ROOT / f"valuation_{TEAM}.csv"
    out.to_csv(path, index=False, encoding="utf-8")

    P.assign(value=value).to_parquet(ROOT / "outputs" / "all_predictions.parquet")
    print(f"index level date: {index.index[-1]}, training sales: {len(X):,}")
    print(f"wrote {path.name}: {len(out):,} rows")
    print(out["value"].describe(percentiles=[0.01, 0.5, 0.99]).round(0).to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
