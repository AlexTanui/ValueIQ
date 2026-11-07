"""Build a local address-lookup demo page: outputs/lookup.html (git-ignored).

The page shows the 31 Aug 2026 value for any supplied address, the evidence
behind it (own last sale, same-building sales and nearby sales, all brought to
Aug 2026 prices with the repeat-sales index), and recent sales in the building.
It contains supplied sale prices, so it must stay local and out of the repo.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.models.price_index import build_index, index_at
from src.predict import INFO_CUTOFF
from src.preprocessing.clean_data import load_properties, load_sales

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
TEMPLATE = Path(__file__).with_name("lookup_template.html")
COMPS_PER_BUILDING = 8


def _dollars(adj, level):
    v = np.exp(adj + level)
    return [None if not np.isfinite(x) else int(round(x, -3)) for x in v]


def main():
    props = load_properties()
    sales = load_sales(props)
    index = build_index(sales, INFO_CUTOFF)
    level = index.iloc[-1]
    P = pd.read_parquet(OUT / "all_predictions.parquet")

    own = _dollars(P["own_last_adj"].to_numpy(), level)
    bldbed = _dollars(P["bldbed_mean"].to_numpy(), level)
    nbr = _dollars(P["nbr_bed_mean"].fillna(P["nbr_mean"]).to_numpy(), level)
    addresses = props.set_index("gnaf_pid").reindex(P["gnaf_pid"])["address"].to_numpy()

    rows = []
    for i, r in enumerate(P.itertuples()):
        rows.append([r.gnaf_pid, f"{addresses[i]}, {r.api_suburb}", int(round(r.value)),
                     None if pd.isna(r.bedrooms) else int(r.bedrooms),
                     None if pd.isna(r.bathrooms) else int(r.bathrooms),
                     None if pd.isna(r.car_spaces) else int(r.car_spaces),
                     r.building_key, round(r.lat, 5), round(r.lng, 5),
                     own[i], None if pd.isna(r.own_years_since) else round(r.own_years_since, 1),
                     bldbed[i], int(r.bldbed_n), nbr[i], int(r.flats_in_building),
                     None if pd.isna(r.floor_est) else int(r.floor_est)])

    s = sales.copy()
    s["today"] = np.exp(s["log_price"] - index_at(index, s["sold_date"]) + level)
    s = s.sort_values("sold_date").groupby("building_key").tail(COMPS_PER_BUILDING)
    addr = props.set_index("gnaf_pid")["address"]
    comps = {}
    for b, g in s.groupby("building_key"):
        comps[b] = [[addr.get(x, ""), d.strftime("%b %Y"), int(p), int(round(t, -3)),
                     None if pd.isna(bd) else int(bd)]
                    for x, d, p, t, bd in zip(g["gnaf_pid"], g["sold_date"], g["sold_price"], g["today"], g["bedrooms"])][::-1]

    idx = np.exp(index - level)
    data = {"rows": rows, "comps": comps,
            "index": {"labels": [str(p) for p in idx.index], "values": [round(float(x), 4) for x in idx]}}
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    (OUT / "lookup.html").write_text(html, encoding="utf-8")
    print(f"outputs/lookup.html written ({len(html) / 1e6:.1f} MB, {len(rows):,} addresses)")


if __name__ == "__main__":
    main()
