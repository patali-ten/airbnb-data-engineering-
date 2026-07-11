"""Load listing_master into a SQLite star schema and run analytical queries."""

import logging
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline_metadata import track_stage

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output" / "sql_output"
LOG_DIR = PROJECT_ROOT / "logs"
DB_PATH = OUTPUT_DIR / "airbnb_edinburgh.db"
REPORT_PATH = OUTPUT_DIR / "analytical_queries_results.md"
CITY = "edinburgh"

SQLITE_TYPE_MAP = {"int64": "INTEGER", "float64": "REAL"}

logger = logging.getLogger("sql_queries")


def setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"load_{date.today().isoformat()}.log"

    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return log_path

FACT_COLUMN_MAP = {
    "id": "listing_id",
    "host_id": "host_id",
    "neighbourhood_cleansed": "neighbourhood",
    "room_type": "room_type",
    "property_type": "property_type",
    "price": "price",
    "occupancy_rate_365": "occupancy_rate_365",
    "estimated_annual_revenue": "estimated_annual_revenue",
    "number_of_reviews": "review_count",
    "review_scores_rating": "avg_review_score",
    "reviews_per_month": "reviews_per_month",
    "price_per_bedroom": "price_per_bedroom",
}

# host_total_listings_count is the InsideAirbnb field the task asks for; note
# it's entirely null in this extract (same gap as host_since below) -- kept
# as-is rather than silently swapped for the populated host_listings_count,
# since that would change what the column means without saying so.
HOST_COLUMN_MAP = {
    "host_id": "host_id",
    "host_since": "host_since",
    "host_tenure_years": "host_tenure_years",
    "host_is_superhost": "host_is_superhost",
    "host_total_listings_count": "host_total_listings_count",
}

NEIGHBOURHOOD_COLUMN_MAP = {
    "neighbourhood_cleansed": "neighbourhood",
    "neighbourhood_group_cleansed": "neighbourhood_group",
    "neighbourhood_median_price": "median_price",
    "neighbourhood_listing_density": "listing_density",
    "neighbourhood_avg_rating": "avg_rating",
}


def build_fact_listing_performance(listing_master: pd.DataFrame) -> pd.DataFrame:
    return listing_master[list(FACT_COLUMN_MAP)].rename(columns=FACT_COLUMN_MAP)


def build_dim_host(listing_master: pd.DataFrame) -> pd.DataFrame:
    # A host can own many listings; host-level attributes should be identical
    # across their rows, so dedupe down to one row per host_id.
    host = listing_master[list(HOST_COLUMN_MAP)].rename(columns=HOST_COLUMN_MAP)
    return host.drop_duplicates(subset="host_id", keep="first").reset_index(drop=True)


def build_dim_neighbourhood(listing_master: pd.DataFrame) -> pd.DataFrame:
    # neighbourhood_median_price/listing_density/avg_rating were computed once
    # per neighbourhood in transform.py and broadcast onto every listing row;
    # dedupe back down to one row per neighbourhood for the dimension table.
    nb = listing_master[list(NEIGHBOURHOOD_COLUMN_MAP)].rename(columns=NEIGHBOURHOOD_COLUMN_MAP)
    return nb.drop_duplicates(subset="neighbourhood", keep="first").reset_index(drop=True)


def create_fact_table(conn: sqlite3.Connection, fact: pd.DataFrame) -> None:
    columns_sql = []
    for col, dtype in fact.dtypes.items():
        sql_type = SQLITE_TYPE_MAP.get(str(dtype), "TEXT")
        constraint = " PRIMARY KEY" if col == "listing_id" else ""
        columns_sql.append(f'"{col}" {sql_type}{constraint}')
    conn.execute(f"CREATE TABLE IF NOT EXISTS fact_listing_performance ({', '.join(columns_sql)})")


def ensure_fact_table_schema(conn: sqlite3.Connection, fact: pd.DataFrame) -> None:
    # INSERT OR REPLACE only dedupes against a real uniqueness constraint. If
    # the table doesn't exist yet, or exists from before this incremental
    # strategy (e.g. an older drop-and-reload run via to_sql, which creates no
    # primary key at all), "CREATE TABLE IF NOT EXISTS" alone would silently
    # keep the old, key-less schema and every "upsert" would just append
    # duplicate rows. Rebuild the table (once) whenever listing_id isn't
    # already its primary key, so the constraint INSERT OR REPLACE relies on
    # actually exists.
    pk_columns = {row[1] for row in conn.execute("PRAGMA table_info(fact_listing_performance)") if row[5] > 0}
    if pk_columns != {"listing_id"}:
        conn.execute("DROP TABLE IF EXISTS fact_listing_performance")
        create_fact_table(conn, fact)


def upsert_fact_listing_performance(conn: sqlite3.Connection, fact: pd.DataFrame) -> None:
    # Incremental load strategy: re-scraping produces a fresh listing_master
    # every time, but most listings haven't actually changed run to run.
    # INSERT OR REPLACE keyed on listing_id (the table's PRIMARY KEY) updates
    # a listing's row in place if it already exists and inserts it if it's
    # new, so a re-run only touches rows whose data changed instead of
    # dropping and rebuilding the whole fact table from scratch each time.
    ensure_fact_table_schema(conn, fact)

    columns = list(fact.columns)
    column_list = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT OR REPLACE INTO fact_listing_performance ({column_list}) VALUES ({placeholders})"

    # NaN/NaT/pd.NA -> None so sqlite3 stores a real SQL NULL instead of the
    # literal float "nan".
    records = fact.astype(object).where(pd.notnull(fact), None).values.tolist()
    conn.executemany(sql, [tuple(row) for row in records])
    conn.commit()


def load_to_sqlite(
    conn: sqlite3.Connection, fact: pd.DataFrame, dim_host: pd.DataFrame, dim_neighbourhood: pd.DataFrame
) -> None:
    # Pandas' nullable Float64 extension dtype isn't accepted by sqlite3's
    # adapter; cast to plain float64 (NA -> NaN -> SQL NULL) just before load.
    fact = fact.astype({col: "float64" for col in fact.select_dtypes("Float64").columns})
    dim_host = dim_host.astype({col: "float64" for col in dim_host.select_dtypes("Float64").columns})
    dim_neighbourhood = dim_neighbourhood.astype(
        {col: "float64" for col in dim_neighbourhood.select_dtypes("Float64").columns}
    )

    upsert_fact_listing_performance(conn, fact)

    # Dimension tables are small lookup tables with no independent
    # "changed since last run" signal per row, so a full replace each run is
    # simplest and cheap -- only the fact table needs incremental upserts.
    dim_host.to_sql("dim_host", conn, if_exists="replace", index=False)
    dim_neighbourhood.to_sql("dim_neighbourhood", conn, if_exists="replace", index=False)


QUERIES = [
    (
        "Top 10 neighbourhoods by median price",
        """
        SELECT neighbourhood, median_price, listing_density, avg_rating
        FROM dim_neighbourhood
        ORDER BY median_price DESC
        LIMIT 10;
        """,
    ),
    (
        "Superhost vs non-superhost: avg occupancy and revenue",
        """
        SELECT
            CASE WHEN h.host_is_superhost = 't' THEN 'Superhost' ELSE 'Non-superhost' END AS host_type,
            COUNT(*) AS listing_count,
            AVG(f.occupancy_rate_365) AS avg_occupancy_rate,
            AVG(f.estimated_annual_revenue) AS avg_estimated_annual_revenue
        FROM fact_listing_performance f
        JOIN dim_host h ON f.host_id = h.host_id
        WHERE h.host_is_superhost IS NOT NULL
        GROUP BY host_type;
        """,
    ),
    (
        "Avg review score by host tenure bucket",
        """
        SELECT
            CASE
                WHEN h.host_tenure_years IS NULL THEN 'Unknown'
                WHEN h.host_tenure_years < 1 THEN '<1yr'
                WHEN h.host_tenure_years < 3 THEN '1-3yr'
                WHEN h.host_tenure_years < 5 THEN '3-5yr'
                ELSE '5yr+'
            END AS tenure_bucket,
            COUNT(*) AS listing_count,
            AVG(f.avg_review_score) AS avg_review_score
        FROM fact_listing_performance f
        JOIN dim_host h ON f.host_id = h.host_id
        GROUP BY tenure_bucket
        ORDER BY
            CASE tenure_bucket
                WHEN '<1yr' THEN 1
                WHEN '1-3yr' THEN 2
                WHEN '3-5yr' THEN 3
                WHEN '5yr+' THEN 4
                ELSE 5
            END;
        """,
    ),
    (
        "Avg estimated annual revenue by room_type",
        """
        SELECT
            room_type,
            COUNT(*) AS listing_count,
            AVG(estimated_annual_revenue) AS avg_estimated_annual_revenue
        FROM fact_listing_performance
        GROUP BY room_type
        ORDER BY avg_estimated_annual_revenue DESC;
        """,
    ),
]


def format_cell(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if value is None:
        return "—"
    return str(value)


def render_result_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows returned._"
    headers = list(df.columns)
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(format_cell(v) for v in row) + " |")
    return "\n".join(lines)


def run_queries(conn: sqlite3.Connection) -> str:
    sections = ["# Analytical Query Results: edinburgh", ""]

    for title, sql in QUERIES:
        result = pd.read_sql_query(sql, conn)

        print(f"\n--- {title} ---")
        print(result.to_string(index=False))

        sections.append(f"## {title}")
        sections.append("")
        sections.append("```sql")
        sections.append(sql.strip())
        sections.append("```")
        sections.append("")
        sections.append(render_result_table(result))
        sections.append("")

    return "\n".join(sections)


def main() -> None:
    log_path = setup_logging()
    logger.info(f"Logging to {log_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    listing_master = pd.read_parquet(PROCESSED_DIR / "listing_master.parquet")
    row_count_in = len(listing_master)

    with track_stage(logger, "load", CITY, row_count_in=row_count_in) as stage:
        fact = build_fact_listing_performance(listing_master)
        dim_host = build_dim_host(listing_master)
        dim_neighbourhood = build_dim_neighbourhood(listing_master)

        conn = sqlite3.connect(DB_PATH)
        try:
            load_to_sqlite(conn, fact, dim_host, dim_neighbourhood)
            stage.row_count_out = conn.execute(
                "SELECT COUNT(*) FROM fact_listing_performance"
            ).fetchone()[0]
            report = run_queries(conn)
        finally:
            conn.close()

        REPORT_PATH.write_text(report, encoding="utf-8")
        logger.info(f"Database written to {DB_PATH}")
        logger.info(f"Query results written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
