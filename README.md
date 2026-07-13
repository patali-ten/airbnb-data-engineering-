# Edinburgh Airbnb Market Intelligence — Data Engineer Intern Assignment

Analysis of 6,244 Airbnb listings in Edinburgh, Scotland, using the Inside Airbnb dataset,
built for Expernetic's Data Engineer Intern technical assessment.

## Review Order

1. `report/report.pdf` — full analysis, findings, and recommendations
2. `notebooks/exploration.ipynb` — annotated EDA and statistical testing, with narrative
3. `docs/decision_log.md` — engineering and analytical decisions with rationale
4. `docs/ai_usage.md` — full AI usage disclosure
5. `src/` — pipeline source code

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

# 6. Train price prediction model + SHAP analysis
python src/model.py
```

All stages log to `logs/` and record run metadata to `output/quality_report/pipeline_metadata.csv`.

## Reproducing the Analysis

```bash
jupyter notebook notebooks/exploration.ipynb
# Kernel → Restart & Run All
```

## Repository Structure

See inline comments in each `src/*.py` file for module-level documentation.
Data quality reports: `output/quality_report/`
Figures: `output/figures/`
SQL query results: `output/sql_output/`

## Data Source

[Inside Airbnb](https://insideairbnb.com/) — Edinburgh, Scotland dataset, licensed under
CC BY 4.0. Raw data is not committed to this repository (see `.gitignore`); run
`src/download.py` to regenerate it.