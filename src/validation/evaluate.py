"""Competition metrics and submission-file checks."""
import numpy as np
import pandas as pd


def metrics(actual, predicted):
    """Within-10% (primary), median abs error (tie-break), MAE, RMSE, R^2."""
    a = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    missing = int(np.isnan(p).sum())
    err = p - a
    # A missing prediction counts as wrong for within-10%.
    within = np.where(np.isnan(p), False, np.abs(err) / a <= 0.10)
    ok = ~np.isnan(p)
    e = err[ok]
    ss_res = float(np.sum(e ** 2))
    ss_tot = float(np.sum((a[ok] - a[ok].mean()) ** 2))
    return {
        "n": len(a),
        "missing": missing,
        "within_10pct": float(within.mean()),
        "within_10pct_count": int(within.sum()),
        "median_abs_error": float(np.median(np.abs(e))),
        "mae": float(np.mean(np.abs(e))),
        "rmse": float(np.sqrt(np.mean(e ** 2))),
        "r2": 1 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
    }


def check_submission(submission_path, input_path, expected_rows=181_711):
    """Raise AssertionError on any submission-format problem; return summary."""
    ids = pd.read_csv(input_path, usecols=["gnaf_id"], dtype=str)["gnaf_id"]
    sub = pd.read_csv(submission_path, dtype={"gnaf_id": str})

    assert len(ids) == expected_rows, f"input has {len(ids)} rows, expected {expected_rows}"
    assert list(sub.columns) == ["gnaf_id", "value"], f"columns are {list(sub.columns)}"
    assert len(sub) == len(ids), f"submission has {len(sub)} rows, input has {len(ids)}"
    assert sub["gnaf_id"].is_unique, "duplicate gnaf_id in submission"
    assert set(sub["gnaf_id"]) == set(ids), "gnaf_id set differs from input"
    assert sub["value"].notna().all(), "null values present"
    assert pd.api.types.is_integer_dtype(sub["value"]), f"value dtype is {sub['value'].dtype}, not integer"
    assert (sub["value"] > 0).all(), "non-positive values present"

    with open(submission_path, encoding="utf-8") as f:
        assert f.readline().strip() == "gnaf_id,value", "unexpected header line"

    return sub["value"].describe(percentiles=[0.01, 0.5, 0.99]).to_dict()


if __name__ == "__main__":
    import sys

    print(check_submission(sys.argv[1], sys.argv[2]))
    print("Submission OK")
