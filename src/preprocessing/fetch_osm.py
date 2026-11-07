"""Download location layers from OpenStreetMap (ODbL, (c) OpenStreetMap contributors)
via the Overpass API, as point sets in data/external/osm_<layer>.csv.

These describe long-standing places (stations, parks, harbour, major roads),
so they are valid as at 31 August 2026.
"""
import time
from pathlib import Path

import pandas as pd
import requests

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "external"
OVERPASS = "https://overpass-api.de/api/interpreter"
BBOX = "-33.935,151.160,-33.845,151.245"  # City of Sydney plus a margin

LAYERS = {
    "stations": f"""(nwr["railway"="station"]({BBOX}); nwr["railway"="halt"]({BBOX});
                     nwr["railway"="tram_stop"]({BBOX}););""",
    "parks": f"""(way["leisure"="park"]({BBOX}); relation["leisure"="park"]({BBOX}););""",
    "water": f"""(way["natural"="coastline"]({BBOX}); way["natural"="water"]({BBOX});
                  relation["natural"="water"]({BBOX}););""",
    "major_roads": f"""(way["highway"~"^(motorway|trunk|primary)$"]({BBOX}););""",
}


def fetch(layer, query):
    q = f"[out:json][timeout:120];{query}out geom;"
    r = requests.post(OVERPASS, data={"data": q}, timeout=180,
                      headers={"User-Agent": "ValuIQ-hackathon/1.0"})
    r.raise_for_status()
    rows = []
    for el in r.json()["elements"]:
        name = el.get("tags", {}).get("name")
        kind = el.get("tags", {}).get("railway") or el.get("tags", {}).get("station")
        if "lat" in el:
            rows.append((el["lat"], el["lon"], name, kind, el["id"]))
        for g in el.get("geometry", []) or []:
            rows.append((g["lat"], g["lon"], name, kind, el["id"]))
        for m in el.get("members", []) or []:
            for g in m.get("geometry", []) or []:
                rows.append((g["lat"], g["lon"], name, kind, el["id"]))
    return pd.DataFrame(rows, columns=["lat", "lng", "name", "kind", "osm_id"])


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for layer, query in LAYERS.items():
        df = fetch(layer, query)
        df.to_csv(OUT_DIR / f"osm_{layer}.csv", index=False)
        print(f"{layer:12s} points={len(df):7,d} features={df['osm_id'].nunique():5,d}")
        time.sleep(2)


if __name__ == "__main__":
    main()
