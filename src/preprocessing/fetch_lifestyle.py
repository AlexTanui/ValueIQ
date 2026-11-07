"""Pull suburb lifestyle data (crime, livability, income, rent, 1-year unit forecast) from the Microburbs API
into data/lifestyle.json (git-ignored).

These are CURRENT indicators, so they are used only by the web app's recommendation
assistant. They are never used as valuation features (31 Aug 2026 information cutoff).
"""
import json
from pathlib import Path

from src.api.microburbs_client import MicroburbsClient

OUT = Path(__file__).resolve().parents[2] / "data" / "lifestyle.json"


def main():
    client = MicroburbsClient()
    suburbs = [s["suburb"] for s in client.get("/v1/suburbs/list")]
    result = {"suburbs": {}, "mb_crime": {}}
    for sub in suburbs:
        crime = client.get(f"/v1/suburbs/{sub}/crime/summary") or {}
        liv = client.get(f"/v1/suburbs/{sub}/lifestyle/livability") or {}
        income = client.get(f"/v1/suburbs/{sub}/demographics/income") or []
        rent = client.get(f"/v1/suburbs/{sub}/market/median-rent") or {}
        mb = client.get(f"/v1/suburbs/{sub}/crime/by-mesh-block") or {}
        forecast = (client.get(f"/v1/suburbs/{sub}/forecast/sale") or {}).get("unit") or {}
        result["suburbs"][sub] = {
            "crime_rate": crime.get("suburb_median"), "crime_verdict": crime.get("verdict"),
            "crime_vs_national_pct": crime.get("vs_national_pct"),
            "scores": {s["key"]: s.get("value") for s in liv.get("scores", [])},
            "median_income": income[0]["median_income"] if income else None,
            "high_income_share": next((b["proportion"] for b in income if b["income_bracket"] == ">$156k"), None),
            "rent_unit_week": rent.get("unit"), "rent_as_of": rent.get("as_of"),
            "forecast_unit_1y": {k: forecast.get(k) for k in ("low", "most_likely", "high")} if forecast else None,
        }
        result["mb_crime"].update({str(k): v for k, v in (mb.get("mesh_blocks") or {}).items()})
        s = result["suburbs"][sub]
        print(f"{sub:28s} crime={s['crime_rate']} safety={s['scores'].get('safety')} income={s['median_income']}")
    OUT.write_text(json.dumps(result))
    print(f"wrote {OUT} ({len(result['mb_crime']):,} mesh blocks with crime rates)")


if __name__ == "__main__":
    main()
