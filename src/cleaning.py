"""Clean the raw Edinburgh Airbnb CSVs and write standardized parquet files to data/processed/."""

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline_metadata import track_stage
from quality_checks import clean_price

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CITY = "edinburgh"
RAW_DIR = PROJECT_ROOT / "data" / "raw" / CITY
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LOG_DIR = PROJECT_ROOT / "logs"
NEIGHBOURHOODS_PATH = RAW_DIR / "neighbourhoods.csv"

PROPERTY_TYPE_MIN_COUNT = 10

logger = logging.getLogger("cleaning")


def setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"cleaning_{date.today().isoformat()}.log"

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


def load_raw() -> dict[str, pd.DataFrame]:
    return {
        "listings": pd.read_csv(RAW_DIR / "listings.csv", low_memory=False),
        "calendar": pd.read_csv(RAW_DIR / "calendar.csv", low_memory=False),
        "reviews": pd.read_csv(RAW_DIR / "reviews.csv", low_memory=False),
    }


def standardize_price_columns(
    listings: pd.DataFrame, calendar: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # price is scraped as a currency string ("$225.50"); downstream numeric work
    # (aggregation, IQR outlier checks) needs a real float, not text.
    listings["price"] = clean_price(listings["price"])

    # This extract's calendar.csv has no price column at all (InsideAirbnb
    # omitted it from this data cut) -- guard instead of assuming it's there.
    if "price" in calendar.columns:
        calendar["price"] = clean_price(calendar["price"])
    else:
        logger.warning("calendar.csv has no 'price' column; skipping price standardization for calendar")

    return listings, calendar


def parse_date_columns(
    listings: pd.DataFrame, calendar: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # host_since/first_review/last_review arrive as ISO date strings (or are
    # entirely absent when a host/listing has no review history yet); casting
    # to datetime lets downstream code do date arithmetic instead of string ops.
    for col in ("host_since", "first_review", "last_review"):
        listings[col] = pd.to_datetime(listings[col], errors="coerce")

    calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce")

    return listings, calendar


def normalize_categoricals(listings: pd.DataFrame) -> pd.DataFrame:
    # Free-text casing/whitespace inconsistencies ("Entire Home/Apt " vs
    # "entire home/apt") would otherwise fragment groupby and join keys.
    listings["room_type"] = listings["room_type"].str.strip().str.lower()
    listings["property_type"] = listings["property_type"].str.strip().str.lower()

    # Long-tail property_type values (fewer than 10 listings) are too sparse to
    # model or chart meaningfully on their own, so they're pooled into 'Other'.
    counts = listings["property_type"].value_counts()
    rare_types = counts[counts < PROPERTY_TYPE_MIN_COUNT].index
    listings.loc[listings["property_type"].isin(rare_types), "property_type"] = "Other"

    return listings


def parse_host_response_rate(listings: pd.DataFrame) -> pd.DataFrame:
    # host_response_rate is scraped as a percentage string ("90%"); coerce to a
    # plain 0-100 float so it's usable numerically. Hosts with no response
    # history stay null rather than being coerced to 0, which would understate them.
    listings["host_response_rate"] = pd.to_numeric(
        listings["host_response_rate"].astype("string").str.rstrip("%"), errors="coerce"
    )
    return listings


def impute_room_medians(listings: pd.DataFrame) -> pd.DataFrame:
    # bedrooms/beds/bathrooms go missing when hosts skip optional fields.
    # Median-by-room_type is a better estimate than a single global median or
    # dropping rows, since a "private room" listing structurally differs in
    # room counts from an "entire home" listing.
    for col in ("bedrooms", "beds", "bathrooms"):
        medians = listings.groupby("room_type")[col].transform("median")
        listings[col] = listings[col].fillna(medians)

    # review_scores_* columns are intentionally left as explicit nulls: a null
    # there means the listing has no reviews yet, not that data was lost, so
    # imputing a score would fabricate a rating that doesn't exist.
    return listings


def standardize_neighbourhoods(listings: pd.DataFrame) -> pd.DataFrame:
    valid_neighbourhoods = set(pd.read_csv(NEIGHBOURHOODS_PATH)["neighbourhood"])

    # Trim incidental whitespace so a name differing only by padding still
    # matches neighbourhoods.csv's canonical spelling exactly.
    listings["neighbourhood_cleansed"] = listings["neighbourhood_cleansed"].str.strip()

    unmatched = ~listings["neighbourhood_cleansed"].isin(valid_neighbourhoods)
    unmatched_count = int(unmatched.sum())
    if unmatched_count:
        sample = sorted(listings.loc[unmatched, "neighbourhood_cleansed"].unique())[:10]
        logger.warning(
            f"{unmatched_count} listings have a neighbourhood_cleansed value not found in "
            f"neighbourhoods.csv, e.g. {sample}"
        )

    return listings


def apply_validation_rules(listings: pd.DataFrame) -> pd.DataFrame:
    # Mirrors the rules reported in quality_checks.py (price >= 0, latitude in
    # [-90, 90], longitude in [-180, 180]); rows failing them are physically
    # impossible / corrupt and unsafe to carry into modeling.
    before = len(listings)

    valid_price = listings["price"].isna() | (listings["price"] >= 0)
    valid_lat = listings["latitude"].between(-90, 90)
    valid_lon = listings["longitude"].between(-180, 180)
    keep_mask = valid_price & valid_lat & valid_lon

    dropped = int((~keep_mask).sum())
    logger.info(
        f"Dropped {dropped} of {before} listings failing validation "
        f"(negative price: {int((~valid_price).sum())}, "
        f"invalid latitude: {int((~valid_lat).sum())}, "
        f"invalid longitude: {int((~valid_lon).sum())})"
    )

    return listings[keep_mask].reset_index(drop=True)


def main() -> None:
    log_path = setup_logging()
    logger.info(f"Logging to {log_path}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_raw()
    listings, calendar, reviews = raw["listings"], raw["calendar"], raw["reviews"]
    row_count_in = len(listings) + len(calendar) + len(reviews)
    logger.info(
        f"Loaded listings ({len(listings)} rows), calendar ({len(calendar)} rows), "
        f"reviews ({len(reviews)} rows)"
    )

    with track_stage(logger, "clean", CITY, row_count_in=row_count_in) as stage:
        listings, calendar = standardize_price_columns(listings, calendar)
        listings, calendar = parse_date_columns(listings, calendar)
        listings = normalize_categoricals(listings)
        listings = parse_host_response_rate(listings)
        listings = impute_room_medians(listings)
        listings = standardize_neighbourhoods(listings)
        listings = apply_validation_rules(listings)

        # reviews.csv's date is parsed for consistency with the other date fields
        # above, so downstream time-based analysis doesn't need its own string parsing.
        reviews["date"] = pd.to_datetime(reviews["date"], errors="coerce")

        listings.to_parquet(PROCESSED_DIR / "listings.parquet", index=False)
        calendar.to_parquet(PROCESSED_DIR / "calendar.parquet", index=False)
        reviews.to_parquet(PROCESSED_DIR / "reviews.parquet", index=False)

        stage.row_count_out = len(listings) + len(calendar) + len(reviews)
        logger.info(
            f"Saved cleaned data to {PROCESSED_DIR}: listings ({len(listings)} rows), "
            f"calendar ({len(calendar)} rows), reviews ({len(reviews)} rows)"
        )


if __name__ == "__main__":
    main()
