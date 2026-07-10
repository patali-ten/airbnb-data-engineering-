"""Profile the raw Edinburgh CSVs and write a schema/quality report to markdown."""

from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CITY = "edinburgh"
DATA_DIR = PROJECT_ROOT / "data" / "raw" / CITY
OUTPUT_PATH = PROJECT_ROOT / "output" / "quality_report" / "schema_profile.md"

SAMPLE_COUNT = 3
MAX_VALUE_LENGTH = 40


def format_value(value) -> str:
    text = str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    if len(text) > MAX_VALUE_LENGTH:
        text = text[: MAX_VALUE_LENGTH - 3] + "..."
    return f"`{text}`"


def format_number(value) -> str:
    if pd.isna(value):
        return "—"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def sample_values(series: pd.Series) -> str:
    samples = series.dropna().unique()[:SAMPLE_COUNT]
    if len(samples) == 0:
        return "—"
    return ", ".join(format_value(v) for v in samples)


def profile_dataframe(df: pd.DataFrame) -> list[dict]:
    rows = []
    for col in df.columns:
        series = df[col]
        is_numeric = pd.api.types.is_numeric_dtype(series)
        null_rate = series.isna().mean() * 100

        rows.append(
            {
                "column": col,
                "dtype": str(series.dtype),
                "null_rate": f"{null_rate:.2f}%",
                "cardinality": series.nunique(),
                "min": format_number(series.min()) if is_numeric else "—",
                "max": format_number(series.max()) if is_numeric else "—",
                "samples": sample_values(series),
            }
        )
    return rows


def render_table(rows: list[dict]) -> str:
    header = "| Column | Dtype | Null Rate | Cardinality | Min | Max | Sample Values |"
    separator = "|---|---|---|---|---|---|---|"
    lines = [header, separator]
    for row in rows:
        lines.append(
            f"| {row['column']} | {row['dtype']} | {row['null_rate']} | "
            f"{row['cardinality']} | {row['min']} | {row['max']} | {row['samples']} |"
        )
    return "\n".join(lines)


def load_csvs(data_dir: Path) -> dict[str, pd.DataFrame]:
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    dataframes = {}
    for csv_path in csv_files:
        print(f"Loading {csv_path.name}...")
        dataframes[csv_path.stem] = pd.read_csv(csv_path, low_memory=False)

    return dataframes


def render_schema_section(dataframes: dict[str, pd.DataFrame]) -> str:
    sections = []
    for name, df in dataframes.items():
        sections.append(f"## {name}.csv")
        sections.append(f"Rows: {len(df)} | Columns: {len(df.columns)}")
        sections.append("")
        sections.append(render_table(profile_dataframe(df)))
        sections.append("")
    return "\n".join(sections)


def orphan_rate(orphan_count: int, total: int) -> dict:
    pct = (orphan_count / total * 100) if total else 0.0
    return {
        "total": total,
        "orphan_count": orphan_count,
        "orphan_pct": f"{pct:.2f}%",
    }


def check_referential_integrity(dataframes: dict[str, pd.DataFrame]) -> list[dict]:
    """Check listing_id uniqueness and foreign-key coverage across the raw files.

    listings.csv's own 'neighbourhood' column is free-text and entirely null in
    this dataset; 'neighbourhood_cleansed' is the standardized field InsideAirbnb
    generates to join against neighbourhoods.csv, so that's used for the FK check.
    """
    checks = []
    listings = dataframes.get("listings")

    if listings is not None and "id" in listings.columns:
        dup_count = int(listings["id"].duplicated().sum())
        checks.append(
            {"check": "listings.csv: id uniqueness", **orphan_rate(dup_count, len(listings))}
        )

        listing_ids = set(listings["id"])
        for child_name in ("calendar", "reviews"):
            child = dataframes.get(child_name)
            if child is not None and "listing_id" in child.columns:
                orphan_count = int((~child["listing_id"].isin(listing_ids)).sum())
                checks.append(
                    {
                        "check": f"{child_name}.csv: listing_id found in listings.csv",
                        **orphan_rate(orphan_count, len(child)),
                    }
                )

        neighbourhoods = dataframes.get("neighbourhoods")
        if (
            neighbourhoods is not None
            and "neighbourhood" in neighbourhoods.columns
            and "neighbourhood_cleansed" in listings.columns
        ):
            valid_neighbourhoods = set(neighbourhoods["neighbourhood"])
            orphan_count = int(
                (~listings["neighbourhood_cleansed"].isin(valid_neighbourhoods)).sum()
            )
            checks.append(
                {
                    "check": "listings.csv: neighbourhood_cleansed found in neighbourhoods.csv",
                    **orphan_rate(orphan_count, len(listings)),
                }
            )

    return checks


def render_integrity_table(checks: list[dict]) -> str:
    header = "| Check | Total Records | Orphaned/Duplicate | Percentage |"
    separator = "|---|---|---|---|"
    lines = [header, separator]
    for check in checks:
        lines.append(
            f"| {check['check']} | {check['total']} | {check['orphan_count']} | {check['orphan_pct']} |"
        )
    return "\n".join(lines)


def render_integrity_section(dataframes: dict[str, pd.DataFrame]) -> str:
    checks = check_referential_integrity(dataframes)
    if not checks:
        return ""
    return "## Referential Integrity\n\n" + render_integrity_table(checks) + "\n"


LISTING_COMPLETENESS_COLUMNS = ["review_scores_rating", "bedrooms", "beds"]


def render_completeness_table(df: pd.DataFrame, columns: list[str]) -> str:
    header = "| Field | Total Records | Missing Count | Missing % |"
    separator = "|---|---|---|---|"
    lines = [header, separator]
    total = len(df)
    for col in columns:
        if col not in df.columns:
            lines.append(f"| {col} | {total} | — | column not found |")
            continue
        missing = int(df[col].isna().sum())
        pct = (missing / total * 100) if total else 0.0
        lines.append(f"| {col} | {total} | {missing} | {pct:.2f}% |")
    return "\n".join(lines)


def calendar_price_null_report(calendar: pd.DataFrame) -> str:
    total = len(calendar)
    if "price" not in calendar.columns:
        return f"`price` column not present in calendar.csv ({total} rows total)."

    missing = int(calendar["price"].isna().sum())
    pct = (missing / total * 100) if total else 0.0
    return f"`price` is null in {missing} / {total} calendar.csv rows ({pct:.2f}%)."


def calendar_date_range_report(calendar: pd.DataFrame) -> str:
    if "date" not in calendar.columns:
        return "`date` column not present in calendar.csv."

    dates = pd.to_datetime(calendar["date"])
    return (
        f"calendar.csv covers {dates.min().date()} to {dates.max().date()} "
        f"({dates.nunique()} unique dates)."
    )


def render_data_quality_section(dataframes: dict[str, pd.DataFrame]) -> str:
    lines = ["## Data Quality Checks", ""]

    listings = dataframes.get("listings")
    if listings is not None:
        lines.append("### Missing Value Rates (listings.csv)")
        lines.append("")
        lines.append(render_completeness_table(listings, LISTING_COMPLETENESS_COLUMNS))
        lines.append("")

    calendar = dataframes.get("calendar")
    if calendar is not None:
        lines.append("### calendar.csv")
        lines.append("")
        lines.append(f"- {calendar_price_null_report(calendar)}")
        lines.append(f"- {calendar_date_range_report(calendar)}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    dataframes = load_csvs(DATA_DIR)

    report = "\n".join(
        [
            f"# Schema Profile: {CITY}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            render_schema_section(dataframes),
            render_data_quality_section(dataframes),
            render_integrity_section(dataframes),
        ]
    )

    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(f"Schema profile written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
