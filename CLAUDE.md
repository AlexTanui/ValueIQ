# ValuIQ: Microburbs Hackathon Project

## 1. Project overview

**Team name:** ValuIQ\
**Hackathon:** The Microburbs Hackathon, Saturday 7 November 2026\
**Selected task:** Task 5 --- Value Every Flat\
**Target area:** City of Sydney, NSW, Australia\
**Primary objective:** Estimate the sale value, as at **31 August
2026**, for every one of the **181,711 supplied G-NAF address IDs**.

ValuIQ is an address-level property valuation solution. It should
combine historical transaction evidence, comparable sales, property
characteristics and location intelligence to produce reliable sale-price
estimates.

The competition's main score is the percentage of predictions within
**10% of the actual sale price** for 227 privately held-out confirmed
flat sales dated 1 September to 4 November 2026. A difference of exactly
10% counts as correct. Teams close to one another are separated using
median absolute dollar error.

The objective is not to build the most complicated model. Prioritise
leakage-free validation, strong features, robust coverage and a correct
submission file.

## 2. Competition rules and data contract

### Valuation date and information cutoff

-   Every prediction must represent the property's estimated sale value
    on **31 August 2026**.
-   Use only information that was available on or before 31 August 2026.
-   Do not use the judges' private sales or prices dated 1 September to
    4 November 2026.
-   Do not use current API information as a historical feature unless
    its source date proves that the information was available by 31
    August 2026.
-   In particular, the API's current property basics must not be used
    for this backdated task unless their source dates are on or before
    the valuation date.
-   Avoid all forms of target leakage, including using future sale
    prices to construct comparable-sales features, market indices,
    repeat-sales adjustments or validation features.

### Supplied files

The hackathon team key and files are expected to be supplied at 11 am on
Saturday 7 November 2026.

1.  `flats-city-of-sydney.csv` --- public input containing 181,711
    unit-style addresses.
2.  `flat-sales-city-of-sydney.csv` --- private historical training
    sales.
3.  `repeat-sales-city-of-sydney.csv` --- historical repeat-sale pairs,
    supplied privately if source rights require it.

These files are for hackathon use only. Do not publish them, commit them
to Git, or include their contents in the public repository.

### Input fields

The input file contains one row per supplied address and includes:

  -----------------------------------------------------------------------
  Field                               Meaning
  ----------------------------------- -----------------------------------
  `gnaf_id`                           Unique G-NAF address ID; required
                                      output key

  `address`                           Street address; may describe a
                                      flat, shop, office or car space

  `suburb`                            One of the 33 City of Sydney
                                      suburbs

  `postcode`                          Postcode

  `mb`                                ABS 2021 mesh-block identifier

  `block_type`                        ABS block classification

  `latitude`, `longitude`             Geographic coordinates

  `unit_number`                       Unit number within the building;
                                      blank for some addresses

  `bedrooms`                          Bedrooms from the last advert held;
                                      blank for many addresses

  `bathrooms`                         Bathrooms from the last advert held

  `car_spaces`                        Car spaces; may be missing

  `flats_in_building`                 Number of flats sharing the street
                                      address; proxy for building size
  -----------------------------------------------------------------------

Important data characteristics: - Approximately 6,700 supplied addresses
contain `SHOP` or `OFFICE` in their names. - The private judging score
only uses sales confirmed as flats. - Bedroom data is missing for a
large proportion of addresses (the brief reports 132,217 missing). -
Some addresses may not represent ordinary residential flats. Handle
these carefully rather than blindly assigning typical apartment values.

### Required output

Create exactly:

`valuation_valuiq.csv`

It must contain: - Exactly two columns: `gnaf_id` and `value`. - All
181,711 input `gnaf_id` values, copied exactly. - No extra IDs and no
duplicate IDs. - One whole-dollar estimated sale price per row. - No
dollar signs or thousands separators. - No blank scored values. A
missing prediction is counted as wrong. - UTF-8 CSV with one header row.

Before submission, verify row count, ID set equality, uniqueness,
non-null predictions, positive and plausible values, integer formatting
and successful CSV reload.

The filename convention is `valuation_<team>.csv`, with the team name
lowercased and spaces changed to hyphens. For ValuIQ, use
`valuation_valuiq.csv`.

## 3. Competition benchmarks

The brief reports the following results from the organiser's 31 August
2026 valuation, assessed against 227 private flat sales under \$1.2
million:

-   Existing Microburbs valuation: within 10% for 34 sales.
-   Suburb median by bedroom count: within 10% for 86 sales.
-   Updating each flat's last sale for citywide price changes: within
    10% for 109 sales.

These are useful benchmarks, not guaranteed validation results for
ValuIQ. The repeat-sales baseline is particularly important to
investigate because it performed best among the stated benchmarks.

## 4. Recommended modelling strategy

Build several complementary approaches and combine them only if
chronological validation demonstrates that the ensemble improves the
competition metric.

### Model A: Comparable-sales valuation

Estimate a property's value using historical sales of similar
properties: - Same building, where reliable building/address matching is
possible. - Nearby properties within the same mesh block or a
geographically defined radius. - Same suburb and similar
bedroom/bathroom/parking configuration. - Similar property type and sale
period.

Use distance, recency and property similarity to weight comparable
sales. Prevent the model from using sales after the relevant prediction
date. Do not use future sale records to calculate historical
comparables.

### Model B: Gradient-boosted machine learning

Start with LightGBM or CatBoost. These models are suitable candidates
for tabular property data and nonlinear interactions.

Potential features: - Suburb, postcode and mesh block. - Latitude and
longitude. - Bedrooms, bathrooms and car spaces. - Missingness
indicators for property attributes. - Flats in building. - Unit number
or carefully derived floor-level features, only where valid and
meaningful. - Historical sale price and date, if available before the
valuation date. - Time-adjusted comparable-sale statistics. -
Neighbourhood and market features whose source dates are valid. -
Property/building-level aggregates calculated without leakage.

Do not assume missing bedroom, bathroom or parking fields mean zero.
Preserve missingness and add missing-value indicators where useful.
Consider sensible imputation, but fit imputers on training data only.

### Model C: Repeat-sales valuation

Identify properties with multiple historical sales. Use the previous
sale price as a property-specific anchor and adjust it for market
movement between the previous sale date and 31 August 2026.

Investigate: - Same-property sale matching. - Sale-date validity and
transaction type. - Duplicate or suspicious records. - Time adjustment
using an index built only from historical sales available by the
valuation date. - Whether citywide, suburb-level or more local price
indices perform best.

Do not treat asking prices, rental estimates or non-sale events as
confirmed sale prices.

### Model D: Baselines

Always build simple baselines before complex models: 1. Overall median
sale price. 2. Suburb median. 3. Suburb-by-bedroom median, with
fallbacks for missing bedrooms. 4. Mesh-block median where sample size
is adequate. 5. Last-sale-price adjusted for market movement.

The baselines are essential for debugging and for deciding whether
complex models genuinely add value.

### Ensemble

Potentially combine: - Comparable-sales prediction. - Gradient-boosted
model prediction. - Repeat-sales prediction. - A robust baseline
fallback.

Determine weights from chronological validation, not intuition. Consider
blending in log-price space if validation supports it. Do not hard-code
arbitrary weights without measuring their effect on the within-10% score
and median absolute error.

## 5. Feature-engineering opportunities

Investigate features that could add information beyond the supplied
columns:

-   Building-level sale history and comparable units.
-   Nearby confirmed flat sales.
-   Mesh-block and suburb price distributions.
-   Distance to the CBD and major employment areas.
-   Public transport access and accessibility.
-   Development applications and planning activity, if date-valid.
-   Building size and density.
-   Floor level, where it can be derived reliably from the unit number
    or other lawful historical data.
-   Aspect, orientation, sunlight and views, only if credible data is
    available.
-   Nearby amenities and neighbourhood characteristics.
-   Historical market movement at city, suburb or local-area level.

A potentially valuable approach is **building-level valuation**:
estimate a baseline for a building from its historical transactions and
comparable units, then adjust for each unit's characteristics. Treat
this as a hypothesis to test, not an assumption that all units in a
building have the same value.

Use only data that the team has the right to use. Record every source
and its licence in `README.md`. Do not scrape websites whose terms
prohibit it. NSW Valuer General bulk sales have non-commercial
restrictions described in the hackathon guide; check the applicable
licence before using or redistributing any data.

## 6. Validation design

The report must state: - The chronological split date. - Number of
training and test sales. - Number of missing predictions. - R-squared. -
The model's own held-out validation results.

A suggested starting design is: - Training: sales before 30 June 2026. -
Validation: sales from 1 July to 31 August 2026.

Check the actual distribution and sample sizes before finalising this
split. The chosen split must be before 31 August 2026. Build features
for each validation property using only information available before
that property's relevant valuation date. Never use the validation sale
price during training or feature construction.

Report these metrics: 1. **Within-10% accuracy** --- primary competition
metric. 2. Median absolute dollar error --- important tie-breaker. 3.
MAE. 4. RMSE. 5. R-squared.

The percentage within 10% is:

`mean(abs(predicted_value - actual_value) / actual_value <= 0.10)`

R-squared must be calculated on held-out observations. Do not choose a
model using R-squared alone. A model can have a high R-squared but a
poor within-10% score.

Use robust fallbacks so every input ID receives a prediction. Ensure all
predictions are positive and finite. Investigate extreme values and
outliers rather than silently clipping without justification.

## 7. Microburbs API integration

### API access

Base URL:

`https://api-ht.microburbs.com.au`

Authentication: bearer token in the HTTP `Authorization` header.

The team key is expected by email at 11 am on hackathon day. Store it in
the environment variable:

`MICROBURBS_API_KEY`

Never hard-code the key, commit it to Git, expose it in browser-side
code, or include it in logs or videos. If an application has a browser
interface, make API requests from the server.

The API covers the City of Sydney's 29 suburbs and addresses. Requests
outside its coverage may return HTTP 403.

### First API call

Example curl:

``` bash
curl 'https://api-ht.microburbs.com.au/v1/properties/GANSW705970502/profile' \
  -H 'Authorization: Bearer YOUR_TEAM_KEY'
```

Example Python:

``` python
import os
import requests

BASE_URL = "https://api-ht.microburbs.com.au"
headers = {
    "Authorization": f"Bearer {os.environ['MICROBURBS_API_KEY']}",
    "Accept": "application/json",
}

response = requests.get(
    f"{BASE_URL}/v1/suburbs/Surry Hills/market/all",
    headers=headers,
    timeout=30,
)
response.raise_for_status()
payload = response.json()
print(payload.get("data"))
```

### Endpoints to investigate

The following endpoints are identified in the hackathon getting-started
material and valuation task brief:

  ----------------------------------------------------------------------------------------------
  Endpoint                                       Potential use           Important caution
  ---------------------------------------------- ----------------------- -----------------------
  `GET /v1/suburbs/list`                         List supported suburbs  Coverage discovery

  `GET /v1/geocode/address`                      Convert address to      Check exact request
                                                 G-NAF ID                parameters in API docs

  `GET /v1/properties/{gnaf_id}/profile`         Property profile        Check source dates

  `GET /v1/properties/{gnaf_id}/valuation/avm`   Existing AVM estimate,  Only about 13%
                                                 range and confidence    coverage; confirm
                                                                         valuation date

  `GET /v1/properties/{gnaf_id}/sale-history`    Sales and adverts for   For this task, use only
                                                 an address              valid `Sold` entries
                                                                         dated by 31 August 2026

  `GET /v1/properties/{gnaf_id}/basics/all`      Current bedrooms,       Do not use unless
                                                 bathrooms and parking   source date is on or
                                                                         before 31 August 2026

  `GET /v1/suburbs/{suburb}/market/all`          Suburb market           Check historical
                                                 indicators              availability and date
                                                                         metadata
  ----------------------------------------------------------------------------------------------

Consult the live API documentation for exact schemas, parameters and
response fields:

https://api-ht.microburbs.com.au/docs

The getting-started guide says: - Start with `/v1/suburbs/list`. - Use
`/v1/geocode/address` to resolve an address to a `gnaf_id`. - A response
with no data can still be HTTP 200 and may look like
`{"data": null, "available": false, "reason": ..., "message": ...}`.
Always check `data` and `available`. - Rate limits are approximately 10
requests per second per key. - On HTTP 429, wait and retry with
backoff. - API output and supplied files must not be put in the public
repository.

The valuation brief states that the AVM endpoint has an indicative cost
of \$0.10 per call and only around 13% of City of Sydney flats have an
AVM. Calling it for all 181,711 addresses could theoretically cost
A\$18,171.10, before accounting for incomplete coverage. Do not make
mass AVM calls without first confirming the team's key allowance,
pricing and permission. Prefer targeted calls and bulk historical data.

### API client implementation guidance

Create a reusable client in `src/api/microburbs_client.py`: - Read the
key from environment variables. - Set request timeouts. - Handle 429
with exponential backoff and a maximum retry count. - Handle 403 and
other HTTP errors explicitly. - Check `available` and `data`. - Cache
responses locally during the hackathon to avoid repeat calls. - Log
endpoint, status and timing but never log the key. - Respect rate
limits. - Store source dates and provenance with every returned
feature. - Do not assume API fields are historically valid.

Example minimal client:

``` python
import os
import time
import requests

BASE_URL = "https://api-ht.microburbs.com.au"

class MicroburbsClient:
    def __init__(self, api_key=None, timeout=30):
        self.api_key = api_key or os.environ["MICROBURBS_API_KEY"]
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        })

    def get(self, path, params=None, max_retries=4):
        url = f"{BASE_URL}{path}"

        for attempt in range(max_retries + 1):
            response = self.session.get(
                url, params=params, timeout=self.timeout
            )

            if response.status_code == 429:
                if attempt == max_retries:
                    response.raise_for_status()
                time.sleep(min(2 ** attempt, 16))
                continue

            response.raise_for_status()
            payload = response.json()

            if not payload.get("available", True):
                return None

            return payload.get("data")

        return None
```

Verify endpoint-specific parameters and response schemas against the
live docs before using this client in production code.

## 8. Suggested repository structure

``` text
valuiq/
├── data/
│   └── .gitkeep
├── src/
│   ├── api/
│   │   └── microburbs_client.py
│   ├── preprocessing/
│   │   └── clean_data.py
│   ├── features/
│   │   └── feature_engineering.py
│   ├── models/
│   │   ├── baseline.py
│   │   ├── lightgbm_model.py
│   │   ├── repeat_sales.py
│   │   ├── comparable_sales.py
│   │   └── ensemble.py
│   ├── validation/
│   │   └── evaluate.py
│   └── predict.py
├── outputs/
│   └── .gitkeep
├── report.html
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
└── CLAUDE.md
```

Keep the code modular but do not over-engineer. The hackathon build
window is only four hours.

Suggested dependencies: - pandas - numpy - requests - scikit-learn -
lightgbm - catboost - scipy - matplotlib (for report charts, if
useful) - python-dotenv (optional, for local `.env` loading)

## 9. Team responsibilities

Adapt these roles to the actual team size (the hackathon allows two to
six members):

  -----------------------------------------------------------------------
  Role                                Responsibility
  ----------------------------------- -----------------------------------
  Team Lead / ML Lead                 Architecture, model selection,
                                      integration and final ensemble

  Data Engineer                       CSV inspection, cleaning, API
                                      integration and feature engineering

  ML Engineer 1                       LightGBM/CatBoost models

  ML Engineer 2                       Repeat-sales and comparable-sales
                                      models

  Validation Engineer                 Temporal validation, leakage checks
                                      and metrics

  Reporting / Integration             Final CSV, report.html, README and
                                      videos
  -----------------------------------------------------------------------

Combine roles if the team has fewer than six members. Keep one person
responsible for final integration and submission checks.

## 10. Four-hour hackathon execution plan

The build window is 11 am to 3 pm.

  -----------------------------------------------------------------------
  Time                                Work
  ----------------------------------- -----------------------------------
  11:00--11:30                        Receive files and key; inspect
                                      schemas, row counts and data
                                      quality

  11:30--12:00                        Clean and join data; establish
                                      leakage-safe feature pipeline

  12:00--12:45                        Build baseline and first
                                      gradient-boosting model

  12:45--1:30                         Add repeat-sales and
                                      comparable-sales features

  1:30--2:00                          Run chronological validation;
                                      compare models and ensemble

  2:00--2:30                          Generate predictions for all
                                      181,711 addresses

  2:30--2:50                          Validate CSV and prepare
                                      `report.html`

  2:50--3:00                          Final checks and upload
  -----------------------------------------------------------------------

If time is running short, prioritise a complete, valid CSV and an honest
validation report over a user interface.

## 11. Required submission

Every team must submit one public repository containing:

### `README.md`

Explain: - What ValuIQ does and who it helps. - Team members and
responsibilities. - Data sources and licences. - How to install and run
the project. - The modelling approach and the key technical idea. - Any
limitations.

### `report.html`

Explain: - Data inspection and cleaning. - Feature engineering. - Model
choices and rationale. - Validation split date. - Training and test
counts. - Within-10% accuracy. - Median absolute error, MAE, RMSE and
R-squared. - Missing predictions. - What worked, what did not and
limitations. - Data provenance and licensing.

### `pitch.mp4`

-   Maximum 45 seconds.
-   Explain what ValuIQ does and why it matters.

### `demo.mp4`

-   Maximum 3 minutes.
-   Show the data, method and working output.
-   Keep each video under 95 MB.
-   For the valuation task, also submit the required CSV.

### Valuation CSV

`valuation_valuiq.csv`

Do not commit the supplied input files, private training data, API key,
API output or hidden judging data to the public repository.

## 12. Final quality-assurance checklist

Before uploading, confirm:

-   [ ] Input file contains the expected 181,711 rows.
-   [ ] Output file is named `valuation_valuiq.csv`.
-   [ ] Output contains exactly `gnaf_id` and `value`.
-   [ ] Every input `gnaf_id` appears exactly once.
-   [ ] There are no extra or duplicate IDs.
-   [ ] There are no blank, null, infinite or non-positive predictions.
-   [ ] Values are whole-dollar numeric values without currency symbols
    or commas.
-   [ ] CSV can be reloaded successfully using pandas.
-   [ ] Validation is chronological and split date is before 31 August
    2026.
-   [ ] No post-31 August 2026 sales or prices were used in features or
    training.
-   [ ] Current API fields have not been treated as historical without
    valid source dates.
-   [ ] Report states split date, test count, missing predictions and
    R-squared.
-   [ ] Report includes the within-10% score and median absolute dollar
    error.
-   [ ] README credits all data sources and licences.
-   [ ] No private files, API keys or API responses are in Git.
-   [ ] Both videos meet duration and file-size limits.
-   [ ] Submission is uploaded before 3 pm.

## 13. Working principles for Claude

When helping develop ValuIQ:

1.  Inspect the actual files and repository before proposing code
    changes. Do not invent column names, schemas, API parameters or file
    paths.
2.  Follow the competition's 31 August 2026 information cutoff strictly.
3.  Treat the private judging period (1 September--4 November 2026) as
    completely unseen.
4.  Use chronological validation and report the exact split date and
    sample counts.
5.  Optimise the within-10% accuracy first, while also monitoring median
    absolute error and R-squared.
6.  Build a simple working baseline before adding complexity.
7.  Make missing-data handling explicit. Do not interpret missing
    bedrooms, bathrooms or parking as zero without evidence.
8.  Make every prediction traceable to valid features and ensure full ID
    coverage.
9.  Do not make expensive or high-volume API calls without checking
    cost, coverage and team-key permissions.
10. Do not expose secrets or place private hackathon data in the public
    repository.
11. Prefer small, testable, reproducible changes. Add checks for row
    counts, duplicate IDs, leakage and output validity.
12. If a proposed feature cannot be shown to have been available by 31
    August 2026, exclude it from the valuation model.
13. Do not fabricate model results, API results, data quality findings
    or validation metrics. Clearly label anything not yet measured.
14. Keep the implementation focused on the CSV and required report. A
    dashboard is optional and must not delay the core deliverables.

## 14. Reference links

-   Hackathon valuation task:
    https://www.microburbs.com.au/p/hackathon-task-valuation
-   Participant guide: https://www.microburbs.com.au/p/hackathon-guide
-   Getting started guide:
    https://www.microburbs.com.au/p/hackathon-getting-started
-   API documentation: https://api-ht.microburbs.com.au/docs
-   Demo applications:
    https://github.com/David-Mib/microburbs-hackathon-demos
-   Live API showcase: https://microburbs-api-demos.vercel.app/
-   Open G-NAF:
    https://data.gov.au/data/dataset/19432f89-dc3a-4ef3-b943-5326ef1dbecc
-   ABS Census: https://www.abs.gov.au/census
-   NSW Planning Portal open data:
    https://www.planningportal.nsw.gov.au/opendata/dataset/online-da-data-api
-   City of Sydney open data: https://data.cityofsydney.nsw.gov.au/
-   NSW Valuer General sales information:
    https://www.nsw.gov.au/housing-and-construction/land-values-nsw/how-to-find-property-sales-information
-   Overture Maps: https://overturemaps.org/
-   OpenStreetMap: https://www.openstreetmap.org/

------------------------------------------------------------------------

**Project identity:** ValuIQ\
**Tagline:** Intelligent Property Valuation Through Data.\
**Final objective:** Deliver a defensible, leakage-free valuation for
every supplied G-NAF ID and maximise the proportion of private judging
sales predicted within 10%.
