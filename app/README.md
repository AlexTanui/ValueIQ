# ValuIQ web app

An interactive map of every supplied City of Sydney address, valued at 31 August 2026. It has three views:

- **Predicted values:** every building, coloured by the median value of its units.
- **Address lookup:** search any address to see its value, the evidence behind it, and recent sales in its building.
- **Model accuracy:** July–August 2026 holdout errors, shown as percentages.
- **Ask ValuIQ:** a plain-English assistant. For example, *"I earn $100k and want a 2 bedroom under $600k in a safe suburb"*. It reads the income or budget, bedrooms, parking, suburbs and lifestyle wishes (safe, quiet, family, vibrant, near a station, near the water), ranks matching flats by ValuIQ value and current suburb data, and pins them on the map. It is rule-based and runs entirely in the browser, with no API key. The lifestyle indicators are current data, used only for recommendations, never in the valuation model.

The app is built with React, Vite and MapLibre GL, on OpenFreeMap vector base maps (no API key needed).

## Run

```bash
# from the repo root, after running the pipeline (src/predict.py and src/validation/run_validation.py)
python -m src.preprocessing.fetch_lifestyle   # suburb lifestyle data (needs MICROBURBS_API_KEY)
python -m src.demo.export_app_data   # writes app/public/data/ (git-ignored: contains supplied sale prices)
cd app && npm install && npm run dev  # open http://localhost:5173
```

The data files are generated locally and never committed. The supplied files and API output must not be published.
