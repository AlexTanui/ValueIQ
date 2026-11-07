# ValuIQ

*Intelligent Property Valuation Through Data.*

ValuIQ estimates the 31 August 2026 sale value of every one of the 181,711 unit-style addresses in the City of Sydney. It was built for Task 5 (Value Every Flat) at the Microburbs Hackathon, 7 November 2026.

> Work in progress. The method, results and run instructions will be filled in during the build.

## Team

| Member | Responsibilities |
| --- | --- |
| TBC | TBC |

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add MICROBURBS_API_KEY
# put the supplied CSVs in data/ (git-ignored)
```

## Data sources and licences

- **Microburbs Hackathon API and supplied files.** Used under the hackathon terms. The supplied files and API output are not included in this repository.
- **Addresses:** Open G-NAF, © Geoscape Australia, licensed by the Commonwealth of Australia under the Open G-NAF End User Licence Agreement (attribution and mailing restriction).
- **2021 mesh-block counts:** ABS Census data, © Commonwealth of Australia, CC BY 4.0. Microburbs' 2026 block figures are estimates, not Census results.
- **Places:** Overture Maps Foundation data and © OpenStreetMap contributors, each under its stated licence.

Any additional data sources will be listed here, each with its licence.
