"""Enrich cleaned listings/calendar data into a single listing_master table."""

import logging
from datetime import date
from pathlib import Path

import pandas as pd

from pipeline_metadata import track_stage

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LOG_DIR = PROJECT_ROOT / "logs"
CITY = "edinburgh"

DAYS_PER_YEAR = 365
AVG_DAYS_PER_MONTH = 30.44

logger = logging.getLogger("transform")


def setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"transform_{date.today().isoformat()}.log"

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


def load_processed() -> tuple[pd.DataFrame, pd.DataFrame]:
    listings = pd.read_parquet(PROCESSED_DIR / "listings.parquet")
    calendar = pd.read_parquet(PROCESSED_DIR / "calendar.parquet")
    return listings, calendar


def compute_occupancy_and_revenue(listings: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    # Inside Airbnb's 'available' flag only distinguishes open vs
    # blocked-or-booked calendar days -- it can't tell a host-imposed block
    # from an actual guest booking. occupancy_rate_365 (and the revenue
    # derived from it below) is therefore a proxy for demand, not a
    # confirmed-bookings figure.
    #
    # Two separate counts are needed: total scraped calendar rows (to detect a
    # listing_id with no calendar coverage at all -> unknown, not 0% occupied)
    # and 't' rows within that (a listing fully booked/blocked has 0 't' rows,
    # which is a real 0, not missing data -- collapsing both cases into one
    # reindex would misreport "fully booked" as "unknown").
    total_days = calendar.groupby("listing_id").size().reindex(listings["id"], fill_value=0)
    available_days = (
        calendar[calendar["available"] == "t"]
        .groupby("listing_id")
        .size()
        .reindex(listings["id"], fill_value=0)
    )

    listings = listings.copy()
    occupancy_rate_365 = (DAYS_PER_YEAR - available_days.values) / DAYS_PER_YEAR
    listings["occupancy_rate_365"] = occupancy_rate_365
    listings.loc[total_days.values == 0, "occupancy_rate_365"] = float("nan")

    # Same proxy caveat applies here: revenue is occupancy x days x nightly
    # price, useful for relative ranking of listings, not real transaction data.
    listings["estimated_annual_revenue"] = (
        listings["occupancy_rate_365"] * DAYS_PER_YEAR * listings["price"]
    )
    return listings


def compute_review_frequency(listings: pd.DataFrame) -> pd.DataFrame:
    today = pd.Timestamp(date.today())
    months_since_first_review = (today - listings["first_review"]).dt.days / AVG_DAYS_PER_MONTH

    # Guard divide-by-zero: listings with no reviews yet (first_review is
    # null) or reviewed within the current month fall back to a frequency of 0
    # instead of NaN/inf.
    safe_months = months_since_first_review.where(months_since_first_review > 0)

    listings = listings.copy()
    listings["review_frequency"] = (listings["number_of_reviews"] / safe_months).fillna(0)
    return listings


def compute_host_tenure(listings: pd.DataFrame) -> pd.DataFrame:
    # host_since being null (no scrape captured it) naturally propagates to a
    # null tenure via NaT arithmetic -- no extra guard needed.
    today = pd.Timestamp(date.today())
    listings = listings.copy()
    listings["host_tenure_years"] = (today - listings["host_since"]).dt.days / DAYS_PER_YEAR
    return listings


def compute_price_per_bedroom(listings: pd.DataFrame) -> pd.DataFrame:
    # Studios/rooms can have 0 recorded bedrooms; flooring the denominator at 1
    # avoids inflating (or div-by-zero-ing) their per-bedroom price.
    listings = listings.copy()
    listings["price_per_bedroom"] = listings["price"] / listings["bedrooms"].clip(lower=1)
    return listings


def compute_neighbourhood_aggregates(listings: pd.DataFrame) -> pd.DataFrame:
    # Neighbourhood-level context (typical price, supply density, typical
    # rating) lets a single listing be compared against its local market
    # rather than the city as a whole.
    neighbourhood_stats = (
        listings.groupby("neighbourhood_cleansed")
        .agg(
            neighbourhood_median_price=("price", "median"),
            neighbourhood_listing_density=("id", "count"),
            neighbourhood_avg_rating=("review_scores_rating", "mean"),
        )
        .reset_index()
    )
    return listings.merge(neighbourhood_stats, on="neighbourhood_cleansed", how="left")


def main() -> None:
    log_path = setup_logging()
    logger.info(f"Logging to {log_path}")

    listings, calendar = load_processed()
    row_count_in = len(listings)

    with track_stage(logger, "transform", CITY, row_count_in=row_count_in) as stage:
        listings = compute_occupancy_and_revenue(listings, calendar)
        listings = compute_review_frequency(listings)
        listings = compute_host_tenure(listings)
        listings = compute_price_per_bedroom(listings)
        listings = compute_neighbourhood_aggregates(listings)

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        listings.to_parquet(PROCESSED_DIR / "listing_master.parquet", index=False)
        listings.to_csv(PROCESSED_DIR / "listing_master.csv", index=False)

        stage.row_count_out = len(listings)
        logger.info(
            f"Wrote listing_master ({len(listings)} rows, {len(listings.columns)} columns) to {PROCESSED_DIR}"
        )


if __name__ == "__main__":
    main()
