"""Distance features from OpenStreetMap layers (see src/preprocessing/fetch_osm.py)."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

EXT_DIR = Path(__file__).resolve().parents[2] / "data" / "external"
EARTH_M = 6_371_000

LOCATION_FEATURES = ["dist_station_m", "stations_800m", "dist_water_m", "dist_park_m", "dist_major_road_m"]


def _tree(layer):
    pts = pd.read_csv(EXT_DIR / f"osm_{layer}.csv")[["lat", "lng"]].drop_duplicates()
    return BallTree(np.radians(pts.to_numpy()), metric="haversine")


def add_location_features(df):
    """Adds LOCATION_FEATURES; NaN everywhere if the OSM files are absent."""
    if not (EXT_DIR / "osm_stations.csv").exists():
        for c in LOCATION_FEATURES:
            df[c] = np.nan
        return df
    q = np.radians(df[["lat", "lng"]].to_numpy())

    stations = pd.read_csv(EXT_DIR / "osm_stations.csv").groupby("osm_id")[["lat", "lng"]].mean()
    st = BallTree(np.radians(stations.to_numpy()), metric="haversine")
    df["dist_station_m"] = st.query(q, k=1)[0][:, 0] * EARTH_M
    df["stations_800m"] = st.query_radius(q, r=800 / EARTH_M, count_only=True)

    for layer, col in [("water", "dist_water_m"), ("parks", "dist_park_m"), ("major_roads", "dist_major_road_m")]:
        df[col] = _tree(layer).query(q, k=1)[0][:, 0] * EARTH_M
    return df
