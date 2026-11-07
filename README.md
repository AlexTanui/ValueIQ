# ValuIQ

*Intelligent Property Valuation Through Data.*

ValuIQ estimates the 31 August 2026 sale value of all 181,711 supplied unit-style addresses in the City of Sydney. It was built for Task 5 (Value Every Flat) at the Microburbs Hackathon, 7 November 2026. It helps lenders, buyers, sellers and councils get a defensible, explainable value for any flat, including flats that haven't sold in years.

**Held-out result:** the cutoff was 1 July 2026, and the model was scored on confirmed flat sales under $1.2M from July–August 2026. **61.6%** were within 10%, with a median absolute error of about **$50k** and an R² of 0.79 across all sales. The mean within-10% across three 2-month folds was 69.2%. The best organiser benchmark in the brief was 48.0%, measured on different sales. Full results, maps and method are in [`report.html`](report.html).

## The key step

**Value the building, then the unit, using only what was known at the time.**

- **Building evidence:** most flats haven't sold recently, but their building and street usually have. We build a quarterly repeat-sales price index and bring every past sale in each building, and every nearby sale, forward to today's prices.
- **The model:** LightGBM learns how to weigh this evidence against the flat's own last sale and its attributes. The evidence is the building × bedroom average, a distance-weighted average of nearby same-bedroom sales, and the flat's own last sale.
- **Point-in-time features:** every feature uses only sales dated strictly before each row's information date, including the training rows.

## How it works

| Step | File |
| --- | --- |
| Load the supplied files, plus API unit sales up to 31 Aug 2026 | `src/preprocessing/fetch_api_data.py`, `src/preprocessing/clean_data.py` |
| Pull stations, parks, water and major roads from OpenStreetMap | `src/preprocessing/fetch_osm.py` |
| Repeat-sales (BMN) quarterly price index | `src/models/price_index.py` |
| Point-in-time building, nearby-sales, mesh-block, grid and suburb features, plus OSM distances | `src/features/` |
| Chronological validation (3 rolling 2-month folds, scored on confirmed flat sales) | `src/validation/run_validation.py` |
| Final 5-seed LightGBM and submission CSV, with built-in format checks | `src/predict.py` |
| Report with maps and charts | `src/report/build_report.py` → `report.html` |
| Interactive web app: value map, address lookup, accuracy map (React + MapLibre) | `app/`, data from `src/demo/export_app_data.py` |

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                        # add MICROBURBS_API_KEY
unzip task5-valuation.zip -d data/task5     # supplied files (git-ignored)

python -m src.preprocessing.fetch_api_data  # about 15 minutes, cached in cache/ (git-ignored)
python -m src.preprocessing.fetch_osm
python -m src.validation.run_validation     # prints fold results and writes outputs/
python -m src.predict                       # writes and checks valuation_valuiq.csv
python -m src.report.build_report           # writes report.html
python -m src.demo.export_app_data          # writes app/public/data/ (git-ignored)
cd app && npm install && npm run dev        # web app at http://localhost:5173
```

## Team

| Member | Responsibilities |
| --- | --- |
| TBC | TBC |

## Data sources and licences

- **Microburbs supplied task files:** input addresses, confirmed flat sales, repeat-sale pairs, and mesh-block homes and people 2021–2026. Used on the day under the hackathon terms and not included in this repository. The 2026 block figures are Microburbs estimates, not Census results.
- **Microburbs Hackathon API:** unit sales up to 31 Aug 2026, used under the hackathon terms. No API output is included in this repository.
- **Addresses:** Open G-NAF, © Geoscape Australia, licensed by the Commonwealth of Australia under the Open G-NAF End User Licence Agreement (attribution and mailing restriction).
- **2021 mesh blocks and Census counts:** ABS, © Commonwealth of Australia, CC BY 4.0.
- **Stations, parks, water and major roads:** © OpenStreetMap contributors, Open Database Licence (ODbL), via the Overpass API.
- **Report base maps:** OpenStreetMap standard tiles, © OpenStreetMap contributors.

## Limitations

- The supplied bedroom, bathroom and parking fields describe the last advert held, and about 73% of addresses have no bedroom count.
- Four suburbs outside the API's coverage (Annandale, Newtown, Paddington and St Peters) rely on the supplied sales only.
- Each validation fold has only 250–400 sales, so differences of 2–3 points between models are within noise.
- Shops, offices and car spaces are valued with the same model and are not the focus.
