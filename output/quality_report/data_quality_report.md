# Data Quality Report: edinburgh
Generated: 2026-07-10 19:33:27

## 1. Exact Duplicate Detection

| Check | Total | Duplicate Rows | Percentage |
|---|---|---|---|
| listings.csv: exact duplicate id | 6244 | 0 | 0.00% |
| calendar.csv: exact duplicate (listing_id, date) | 2284170 | 0 | 0.00% |

- No exact duplicates found for listings.csv — safe to use as a key.
- No exact duplicates found for calendar.csv — safe to use as a key.

## 2. Fuzzy Duplicate Detection

Flagged 151 listings across 63 groups sharing the same host_id, rounded (4dp) lat/long, and a price within 5% of each other — likely relisted or duplicate units.
- Flagged rows exported to `output\quality_report\duplicates.csv`.

## 3. Outlier Detection (IQR)

| Field | Lower Bound | Upper Bound | Evaluated | Outlier Count | Outlier % |
|---|---|---|---|---|---|
| price | -130.47 | 622.28 | 5610 | 283 | 5.04% |
| minimum_nights | -0.5 | 3.5 | 6242 | 342 | 5.48% |
| number_of_reviews | -205.0 | 363.0 | 6244 | 456 | 7.30% |

- **price**: 283 outliers (5.04%) outside [-130.47, 622.28] (1.5×IQR).
- **minimum_nights**: 342 outliers (5.48%) outside [-0.5, 3.5] (1.5×IQR).
- **number_of_reviews**: 456 outliers (7.30%) outside [-205.0, 363.0] (1.5×IQR).
- 1049 unique listings flagged on at least one field; exported to `output\quality_report\outliers.csv`.

## 4. Validation Rule Violations

| Rule | Evaluated | Violations | Percentage |
|---|---|---|---|
| price >= 0 | 5610 | 0 | 0.00% |
| latitude in [-90, 90] | 6244 | 0 | 0.00% |
| longitude in [-180, 180] | 6244 | 0 | 0.00% |
| availability_365 in [0, 365] | 6244 | 0 | 0.00% |

- No violations of `price >= 0`.
- No violations of `latitude in [-90, 90]`.
- No violations of `longitude in [-180, 180]`.
- No violations of `availability_365 in [0, 365]`.
