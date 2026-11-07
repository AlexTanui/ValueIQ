"""Value every supplied address at 31 August 2026 and write the submission CSV.

Information cutoff: sales dated on or before 31 August 2026 only. The index,
training set and features all come from that history. Output IDs are exactly
the IDs in data/task5/flats-city-of-sydney.csv.

Usage: python -m src.predict
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.feature_engineering import build_features
from src.models.price_index import build_index
from src.preprocessing.clean_data import TASK_DIR, VALUATION_DATE, load_properties, load_sales
from src.validation.evaluate import check_submission
from src.validation.run_validation import fit_lgb, predict_adj, training_frame

ROOT = Path(__file__).resolve().parents[1]
TEAM = "valuiq"
INFO_CUTOFF = VALUATION_DATE + pd.Timedelta(days=1)  # sales strictly before this are usable


def main():
    props = load_properties()
    sales = load_sales(props)
    index = build_index(sales, INFO_CUTOFF)
    level = index.iloc[-1]

    X = training_frame(sales, INFO_CUTOFF, index)
    models = fit_lgb(X)

    props["info_date"] = INFO_CUTOFF
    P = build_features(props, sales, index)
    value = np.exp(predict_adj(models, P)["lightgbm_seed_avg"] + level)
    assert np.isfinite(value).all() and (value > 0).all(), "non-finite or non-positive predictions"

    out = pd.DataFrame({"gnaf_id": P["gnaf_pid"].astype(str), "value": np.round(value).astype("int64")})
    path = ROOT / f"valuation_{TEAM}.csv"
    out.to_csv(path, index=False, encoding="utf-8")
    P.assign(value=value).to_parquet(ROOT / "outputs" / "all_predictions.parquet")

    summary = check_submission(path, TASK_DIR / "flats-city-of-sydney.csv")
    print(f"index quarter: {index.index[-1]}, training sales: {len(X):,}, seeds: {len(models)}")
    print(f"wrote {path.name}: {len(out):,} rows, submission checks passed")
    print({k: round(v) for k, v in summary.items()})


if __name__ == "__main__":
    main()
