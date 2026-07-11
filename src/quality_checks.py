"""Duplicate, outlier, and validation checks for the raw Edinburgh Airbnb data.

Reuses the CSV loading from profiling.py and writes:
- output/quality_report/duplicates.csv  (fuzzy relisted/duplicate units)
- output/quality_report/outliers.csv    (IQR outliers on price/minimum_nights/number_of_reviews)
- output/quality_report/data_quality_report.md (combined narrative report)
"""

from datetime import datetime

import pandas as pd

from profiling import CITY, DATA_DIR, PROJECT_ROOT, load_csvs

OUTPUT_DIR = PROJECT_ROOT / "output" / "quality_report"
DUPLICATES_PATH = OUTPUT_DIR / "duplicates.csv"
OUTLIERS_PATH = OUTPUT_DIR / "outliers.csv"
REPORT_PATH = OUTPUT_DIR / "data_quality_report.md"

PRICE_TOLERANCE = 0.05
LAT_LON_DECIMALS = 4
IQR_MULTIPLIER = 1.5
OUTLIER_FIELDS = {"price_numeric": "price", "minimum_nights": "minimum_nights", "number_of_reviews": "number_of_reviews"}


def pct(count: int, total: int) -> str:
    return f"{(count / total * 100) if total else 0.0:.2f}%"


def clean_price(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.replace(r"[$,]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def prepare_listings(listings: pd.DataFrame) -> pd.DataFrame:
    df = listings.copy()
    df["price_numeric"] = clean_price(df["price"])
    return df


# --- 1. Exact duplicate detection -----------------------------------------


def exact_duplicate_checks(listings: pd.DataFrame, calendar: pd.DataFrame) -> list[dict]:
    listing_dup_count = int(listings["id"].duplicated(keep=False).sum())
    calendar_dup_count = int(calendar.duplicated(subset=["listing_id", "date"], keep=False).sum())

    return [
        {
            "check": "listings.csv: exact duplicate id",
            "total": len(listings),
            "count": listing_dup_count,
            "pct": pct(listing_dup_count, len(listings)),
        },
        {
            "check": "calendar.csv: exact duplicate (listing_id, date)",
            "total": len(calendar),
            "count": calendar_dup_count,
            "pct": pct(calendar_dup_count, len(calendar)),
        },
    ]


# --- 2. Fuzzy duplicate detection ------------------------------------------


def _find(parent: dict[int, int], x: int) -> int:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _union(parent: dict[int, int], a: int, b: int) -> None:
    ra, rb = _find(parent, a), _find(parent, b)
    if ra != rb:
        parent[ra] = rb


def detect_fuzzy_duplicates(listings: pd.DataFrame) -> pd.DataFrame:
    """Flag listings sharing host_id, 4-decimal lat/long, and price within 5%.

    Connected components (union-find) are used so that a fuzzy_group reflects an
    actual chain of price-similar listings, rather than everything at the same
    host/location — two unrelated price pairs at the same building shouldn't be
    merged into one group just because the location key matches.
    """
    df = listings.copy()
    df["lat_rounded"] = df["latitude"].round(LAT_LON_DECIMALS)
    df["lon_rounded"] = df["longitude"].round(LAT_LON_DECIMALS)

    parent: dict[int, int] = {}

    for _, group in df.groupby(["host_id", "lat_rounded", "lon_rounded"]):
        priced = group.dropna(subset=["price_numeric"])
        if len(priced) < 2:
            continue

        idx = priced.index.tolist()
        prices = priced["price_numeric"]
        for i in idx:
            parent.setdefault(i, i)

        for i in range(len(idx)):
            for j in range(i + 1, len(idx)):
                p1, p2 = prices.iloc[i], prices.iloc[j]
                avg = (p1 + p2) / 2
                within = (p1 == p2 == 0) or (avg > 0 and abs(p1 - p2) / avg <= PRICE_TOLERANCE)
                if within:
                    _union(parent, idx[i], idx[j])

    components: dict[int, list[int]] = {}
    for i in parent:
        components.setdefault(_find(parent, i), []).append(i)
    matched_components = [members for members in components.values() if len(members) > 1]

    columns = ["id", "host_id", "latitude", "longitude", "price", "price_numeric"]
    if not matched_components:
        return pd.DataFrame(columns=columns + ["fuzzy_group"])

    matched_indices = {
        member: gid for gid, members in enumerate(matched_components, start=1) for member in members
    }

    flagged = df.loc[list(matched_indices.keys()), columns].copy()
    flagged["fuzzy_group"] = [matched_indices[i] for i in flagged.index]
    return flagged.sort_values(["fuzzy_group", "id"]).reset_index(drop=True)


# --- 3. IQR outlier detection ------------------------------------------


def iqr_bounds(series: pd.Series) -> tuple[float, float]:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return q1 - IQR_MULTIPLIER * iqr, q3 + IQR_MULTIPLIER * iqr


def detect_outliers(listings: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    df = listings.copy()
    flags = pd.DataFrame(index=df.index)
    summary = []

    for col, label in OUTLIER_FIELDS.items():
        series = df[col]
        valid = series.dropna()
        lower, upper = iqr_bounds(valid)
        mask = ((series < lower) | (series > upper)).fillna(False)
        flags[f"{label}_outlier"] = mask

        outlier_count = int(mask.sum())
        summary.append(
            {
                "field": label,
                "lower_bound": round(lower, 2),
                "upper_bound": round(upper, 2),
                "evaluated": int(valid.shape[0]),
                "outlier_count": outlier_count,
                "outlier_pct": pct(outlier_count, int(valid.shape[0])),
            }
        )

    any_outlier = flags.any(axis=1)
    export_columns = ["id", "host_id", "price", "price_numeric", "minimum_nights", "number_of_reviews"]
    flagged = df.loc[any_outlier, export_columns].copy()
    for flag_col in flags.columns:
        flagged[flag_col] = flags.loc[any_outlier, flag_col]

    return flagged.reset_index(drop=True), summary


# --- 4. Validation rules ------------------------------------------


def validation_checks(listings: pd.DataFrame) -> list[dict]:
    total = len(listings)
    price_valid = listings["price_numeric"].dropna()

    price_violations = int((price_valid < 0).sum())
    lat_violations = int((~listings["latitude"].between(-90, 90)).sum())
    lon_violations = int((~listings["longitude"].between(-180, 180)).sum())
    avail_violations = int((~listings["availability_365"].between(0, 365)).sum())

    return [
        {
            "rule": "price >= 0",
            "evaluated": len(price_valid),
            "violations": price_violations,
            "pct": pct(price_violations, len(price_valid)),
        },
        {
            "rule": "latitude in [-90, 90]",
            "evaluated": total,
            "violations": lat_violations,
            "pct": pct(lat_violations, total),
        },
        {
            "rule": "longitude in [-180, 180]",
            "evaluated": total,
            "violations": lon_violations,
            "pct": pct(lon_violations, total),
        },
        {
            "rule": "availability_365 in [0, 365]",
            "evaluated": total,
            "violations": avail_violations,
            "pct": pct(avail_violations, total),
        },
    ]


# --- Report rendering ------------------------------------------


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def build_report(
    exact_checks: list[dict],
    fuzzy_df: pd.DataFrame,
    outlier_summary: list[dict],
    outlier_df: pd.DataFrame,
    validation: list[dict],
) -> str:
    sections = [
        f"# Data Quality Report: {CITY}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. Exact Duplicate Detection",
        "",
        render_table(
            ["Check", "Total", "Duplicate Rows", "Percentage"],
            [[c["check"], c["total"], c["count"], c["pct"]] for c in exact_checks],
        ),
        "",
    ]

    for c in exact_checks:
        if c["count"] == 0:
            sections.append(f"- No exact duplicates found for {c['check'].split(':')[0]} — safe to use as a key.")
        else:
            sections.append(
                f"- {c['count']} rows ({c['pct']}) are exact duplicates for {c['check'].split(':')[0]} "
                "and should be deduplicated before modeling."
            )
    sections.append("")

    fuzzy_groups = fuzzy_df["fuzzy_group"].nunique() if not fuzzy_df.empty else 0
    sections += [
        "## 2. Fuzzy Duplicate Detection",
        "",
        (
            f"Flagged {len(fuzzy_df)} listings across {fuzzy_groups} groups sharing the same host_id, "
            f"rounded (4dp) lat/long, and a price within {int(PRICE_TOLERANCE * 100)}% of each other — "
            "likely relisted or duplicate units."
            if len(fuzzy_df) > 0
            else "No fuzzy duplicate candidates found (same host, same rounded coordinates, price within "
            f"{int(PRICE_TOLERANCE * 100)}%)."
        ),
        f"- Flagged rows exported to `{DUPLICATES_PATH.relative_to(PROJECT_ROOT)}`.",
        "",
    ]

    sections += [
        "## 3. Outlier Detection (IQR)",
        "",
        render_table(
            ["Field", "Lower Bound", "Upper Bound", "Evaluated", "Outlier Count", "Outlier %"],
            [
                [s["field"], s["lower_bound"], s["upper_bound"], s["evaluated"], s["outlier_count"], s["outlier_pct"]]
                for s in outlier_summary
            ],
        ),
        "",
    ]
    for s in outlier_summary:
        sections.append(
            f"- **{s['field']}**: {s['outlier_count']} outliers ({s['outlier_pct']}) outside "
            f"[{s['lower_bound']}, {s['upper_bound']}] (1.5×IQR)."
        )
    sections += [
        f"- {len(outlier_df)} unique listings flagged on at least one field; exported to "
        f"`{OUTLIERS_PATH.relative_to(PROJECT_ROOT)}`.",
        "",
    ]

    sections += [
        "## 4. Validation Rule Violations",
        "",
        render_table(
            ["Rule", "Evaluated", "Violations", "Percentage"],
            [[v["rule"], v["evaluated"], v["violations"], v["pct"]] for v in validation],
        ),
        "",
    ]
    for v in validation:
        if v["violations"] == 0:
            sections.append(f"- No violations of `{v['rule']}`.")
        else:
            sections.append(f"- {v['violations']} rows ({v['pct']}) violate `{v['rule']}`.")

    return "\n".join(sections) + "\n"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataframes = load_csvs(DATA_DIR)
    listings = prepare_listings(dataframes["listings"])
    calendar = dataframes["calendar"]

    exact_checks = exact_duplicate_checks(listings, calendar)
    fuzzy_df = detect_fuzzy_duplicates(listings)
    outlier_df, outlier_summary = detect_outliers(listings)
    validation = validation_checks(listings)

    fuzzy_df.to_csv(DUPLICATES_PATH, index=False)
    outlier_df.to_csv(OUTLIERS_PATH, index=False)

    report = build_report(exact_checks, fuzzy_df, outlier_summary, outlier_df, validation)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(f"Duplicates written to {DUPLICATES_PATH}")
    print(f"Outliers written to {OUTLIERS_PATH}")
    print(f"Data quality report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
