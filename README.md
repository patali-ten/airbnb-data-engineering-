# Edinburgh Airbnb Market Intelligence — Data Engineer Intern Assignment

**Candidate:** Patali Tennakoon
**Submitted to:** Expernetic (Pvt) Ltd — Data Engineer Intern Talent Assessment Program
**City analyzed:** Edinburgh, Scotland (single-city, by deliberate scope decision — see report Section 2.3)

Full data engineering pipeline and analysis of 6,244 active Airbnb listings across 111
Edinburgh neighbourhoods, using the public Inside Airbnb dataset. Covers ingestion,
cleaning, star-schema modeling, exploratory analysis, hypothesis testing, and a
Random Forest price-prediction model with SHAP explainability.

## Review Order

Recommended order to review this submission:

1. `report/report.pdf` — full findings, methodology, and business recommendations (start here)
2. `README.md` — this file, for setup and navigation
3. `notebooks/exploration.ipynb` — annotated EDA and statistical testing, with narrative interpretation
4. `docs/decision_log.md` — engineering and analytical decisions, with rationale and trade-offs
5. `docs/ai_usage.md` — full AI usage disclosure (Claude.ai + Claude Code, validation methodology, all prompts)
6. `src/` — pipeline source code

## Repository Structure

```
airbnb-data-engineering/
├── README.md                    ← this file
├── requirements.txt
├── .gitignore
├── config/
│   └── city_config.yaml         ← pipeline config (city, source URLs)
├── report/
│   └── report.pdf                ← primary deliverable
├── data/
│   ├── raw/                     ← gitignored, regenerated via download.py
│   └── processed/                ← gitignored, regenerated via pipeline
├── src/
│   ├── download.py               ← ingestion
│   ├── profiling.py              ← schema profiling, quality checks, duplicates/outliers
│   ├── cleaning.py               ← standardization, imputation, validation
│   ├── transform.py              ← enrichment, derived fields, master table
│   ├── sql_queries.py            ← star schema build (SQLite) + analytical queries
│   ├── stats_tests.py            ← hypothesis testing functions
│   ├── regression.py             ← correlation matrix, OLS regression, VIF
│   └── model.py                  ← Random Forest price model + SHAP
├── notebooks/
│   └── exploration.ipynb         ← EDA + hypothesis testing, annotated
├── output/
│   ├── figures/                  ← all chart images (also embedded in report)
│   ├── quality_report/           ← data quality report, duplicates, outliers, model performance
│   └── sql_output/                ← analytical query results
├── logs/                          ← pipeline run logs
└── docs/
├── decision_log.md
└── ai_usage.md
```

## Setup

```bash
git clone <repo-url>
cd airbnb-data-engineering
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running the Pipeline

```bash
# 1. Download and extract raw data
python src/download.py --city edinburgh

# 2. Profile and quality-check raw data
python src/profiling.py

# 3. Clean and standardize
python src/cleaning.py

# 4. Enrich and join into master table
python src/transform.py

# 5. Build star schema and run analytical queries
python src/sql_queries.py

# 6. Run hypothesis tests and regression
python src/stats_tests.py
python src/regression.py

# 7. Train price prediction model + SHAP analysis
python src/model.py
```

All stages log to `logs/` and record run metadata to `output/quality_report/pipeline_metadata.csv`.
The pipeline uses upsert-based incremental loading (`INSERT OR REPLACE` on `listing_id`), so
re-running steps 5–7 after a fresh download will not duplicate records.

## Reproducing the Analysis

```bash
jupyter notebook notebooks/exploration.ipynb
# Kernel → Restart & Run All
```

## Key Results (see report.pdf for full detail)

- Entire-home listings command £150–163 more per night than private rooms (large effect)
- Top 10% of hosts control ~40% of all Edinburgh listings
- Random Forest price model: log-scale R² = 0.66, MAE = £86.52/night (42.8% improvement over baseline)

## Data Source

[Inside Airbnb](https://insideairbnb.com/) — Edinburgh, Scotland dataset, licensed under
CC BY 4.0. Raw data is not committed to this repository (see `.gitignore`); run
`src/download.py` to regenerate it.

## Data & Privacy Note

This repository contains no credentials, API keys, or personal data. All data used is
Inside Airbnb's publicly available, anonymized dataset.