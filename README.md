# ValuIQ

*Intelligent Property Valuation Through Data.*

ValuIQ estimates the 31 August 2026 sale value of every unit-style address in the City of Sydney. It was built for Task 5 (Value Every Flat) at the Microburbs Hackathon, 7 November 2026. It helps lenders, buyers, sellers and councils get a defensible, explainable value for any flat, including flats that haven't sold in years.

**Held-out result:** the cutoff was 1 July 2026 and the model was scored on July–August 2026 sales under $1.2M. **62.8%** of valuations were within 10%, with a median absolute error of about $53k. The best organiser benchmark in the brief was 48.0%. The full results, maps and method are in [`report.html`](report.html).

## The key step

**Value the building, then the unit.** Most flats haven't sold recently, but their building usually has. We build a quarterly repeat-sales price index from 66,000+ same-flat sale pairs, bring every past sale in each building forward to today's prices with it, and group the results by bedroom count. LightGBM then learns how much weight to give that building evidence compared with the flat's own last sale, the neighbourhood, and the unit's attributes. Every feature is **point-in-time**: it is built only from sales dated strictly before each row's information date, including in training.

## How it works

| Step | File |
| --- | --- |
| Pull every address and all sales up to 31 Aug 2026 from the Microburbs API | `src/preprocessing/fetch_api_data.py` |
| Pull stations, parks, water and major roads from OpenStreetMap | `src/preprocessing/fetch_osm.py` |
| Clean: unit sales only, drop bulk/en-bloc sales, derive building, floor and flags | `src/preprocessing/clean_data.py` |
| Repeat-sales (BMN) quarterly price index | `src/models/price_index.py` |
| Point-in-time building, mesh-block, grid and suburb features, plus OSM distances | `src/features/` |
| Chronological validation (3 rolling 2-month folds) | `src/validation/run_validation.py` |
| Final model and submission CSV | `src/predict.py` |
| Report with maps and charts | `src/report/build_report.py` → `report.html` |

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                        # add MICROBURBS_API_KEY

python -m src.preprocessing.fetch_api_data  # about 15 minutes, cached in cache/ (git-ignored)
python -m src.preprocessing.fetch_osm
python -m src.validation.run_validation     # prints fold results and writes outputs/
python -m src.predict [data/flats-city-of-sydney.csv]   # writes valuation_valuiq.csv
python -m src.validation.evaluate valuation_valuiq.csv <input.csv>   # submission checks
python -m src.report.build_report           # writes report.html
```

## Team

| Member | Responsibilities |
| --- | --- |
| TBC | TBC |

## Data sources and licences

- **Microburbs Hackathon API**: addresses, property attributes, sales and suburb data, used under the hackathon terms. No API output or supplied files are included in this repository.
- **Addresses:** Open G-NAF, © Geoscape Australia, licensed by the Commonwealth of Australia under the Open G-NAF End User Licence Agreement (attribution and mailing restriction).
- **2021 mesh blocks:** ABS, © Commonwealth of Australia, CC BY 4.0. Microburbs' 2026 block figures are estimates, not Census results.
- **Stations, parks, water and major roads:** © OpenStreetMap contributors, Open Database Licence (ODbL), via the Overpass API.
- **Report base maps:** OpenStreetMap standard tiles, © OpenStreetMap contributors.

## Limitations

- The supplied input file wasn't received, so by default the IDs come from the API's address list. Passing the official input CSV to `src/predict.py` restricts the output to exactly those IDs.
- The API's bedroom, bathroom and parking fields come from each address's latest advert, and their source dates aren't exposed.
- The validation holdout has a few hundred sales, so differences of about 2–3 points between models are within noise.
- Houses, shops and offices are valued with the unit model and are not the focus.
