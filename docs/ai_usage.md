# AI Usage Log

## Validation Philosophy

All AI-generated code in this project (download.py, profiling.py, and any subsequent pipeline 
scripts) was executed locally and its output checked before being trusted for report figures or 
downstream decisions. Validation took three forms, applied depending on the task:

1. **Direct verification** — for file operations (e.g. download.py), confirming expected files exist 
   on disk with non-zero size, rather than trusting a "success" log message alone.
2. **Cross-checking against raw data** — for analytical scripts (e.g. profiling.py), spot-checking a 
   sample of computed values (null counts, cardinality, date ranges) against a manual pandas read of 
   the same CSV, to catch cases where the generated code silently mishandled a data type or edge case.
3. **Judgment on interpretive output** — for AI-drafted prose (report paragraphs, decision log 
   entries), verifying every cited number against the underlying schema_profile.md or script output 
   before accepting the text, and applying independent judgment on any assumption the AI proposed 
   (e.g. the bedrooms-as-studio heuristic) rather than accepting it uncritically.

No AI-generated numeric claim in this report was used without being traced back to its source in the 
raw data or a validated script output. Where AI output was factually wrong or needed correction, this 
is noted in the "Modified?" column below.


| Date | Tool / Model | Task | Key Prompt (summary) | Validation Done | Modified? |
|---|---|---|---|---|---|
| 2026-07-09 | Claude.ai (Sonnet) | City selection recommendation + report justification | Asked for city recommendation (avoiding NYC/London/Paris) and a 2-3 sentence justification for §2.2 | Reviewed reasoning against assignment scope, agreed with dataset-size/seasonality trade-off | Used with minor wording tweaks |
| 2026-07-09 | Claude Code (Sonnet) | Wrote download.py | "Write a script to download & decompress Inside Airbnb files with retry logic and logging" | Ran script, confirmed 5 files present in data/raw/edinburgh/, checked file sizes are non-zero | No changes needed |
| 2026-07-09 | Claude Code (Sonnet) | Wrote profiling.py (initial schema profiler) | "Profile each CSV: dtypes, nulls, cardinality, sample values, output to markdown" | Manually reviewed output vs. opening 2 CSVs directly in pandas to spot-check counts | Fixed date parsing on last_scraped column |
| 2026-07-10 | Claude Code (Sonnet) | Added referential integrity checks to profiling.py | "Add a function that checks: is listing_id unique in listings.csv? Does every listing_id in calendar.csv and reviews.csv exist in listings.csv? Does every neighbourhood in listings.csv exist in neighbourhoods.csv? Report orphaned records as counts and percentages" | Spot-checked a sample of flagged orphaned listing_ids manually against listings.csv | No changes needed |
| 2026-07-10 | Claude Code (Sonnet) | Added missingness + calendar date-range reporting to profiling.py | "Report the % of listings with missing review_scores_rating, bedrooms, and beds. Count how many calendar rows have price = null. Also report the date range covered by calendar.csv" | Cross-checked missing counts against schema_profile.md null rates for consistency | No changes needed |
| 2026-07-10 | Claude.ai (Sonnet) | Drafted decision_log.md entries for ambiguous-field assumptions | Asked to turn schema_profile.md findings (100%-null columns, bedrooms/beds/bathrooms missingness, license field, price missingness) into decision-log entries with rationale and trade-offs | Verified each null-rate figure cited against schema_profile.md before accepting | Accepted with no numeric changes; own judgment applied on the bedrooms=studio assumption |
| 2026-07-10 | Claude.ai (Sonnet) | Drafted §3.1 business domain context paragraph | Asked for a 3-4 sentence explanation of what listing/host/review/calendar represent, grounded in the actual dataset stats (e.g. calculated_host_listings_count range, calendar date coverage) | Checked cited ranges (1-116 host listings count, 2026-06-23 to 2027-07-01 calendar range) against schema_profile.md | Used with no changes |
| 2026-07-10 | Claude.ai (Sonnet) | Drafted §3.3 summary paragraph on ambiguous-field assumptions | Asked for a report-ready summary of decision_log.md assumptions that points readers to the full log | Compared summary against decision_log.md for accuracy, no invented details | Used with no changes |
| 2026-07-10 | Claude Code (Sonnet) | Duplicate/outlier/validation checks | "Add deterministic + fuzzy duplicate detection, IQR outliers, validation rules, compile into data quality report" | Manually spot-checked 5 flagged duplicates against raw listings.csv on Airbnb-style fields; confirmed outlier thresholds aren't excluding legitimate luxury listings | Adjusted fuzzy-match price tolerance from 10% to 5% after reviewing false positives |
| 2026-07-10 | Claude Code (Sonnet) | Cleaning & standardization pipeline | "Standardize price/dates, normalize categoricals, impute missing values by strategy, drop validation failures, save to parquet" | Compared row counts before/after; verified price column has no nulls/strings left with dtype check; spot-checked 5 imputed bedroom values against room_type | Changed bedroom imputation from mean to median (right-skewed distribution) |
| 2026-07-10 | Claude Code (Sonnet) | Enrichment: occupancy, revenue, tenure, neighbourhood aggregates | "Compute derived fields and neighbourhood aggregates, join into master table" | Checked estimated_annual_revenue distribution for sanity (no negative/absurd values); confirmed neighbourhood aggregates sum correctly against raw listing counts | None |
| 2026-07-10 | Claude Code (Sonnet) | Star schema + analytical SQL queries | "Build fact/dim tables in SQLite, write 4 analytical queries" | Ran each query manually, cross-checked query 1 result (top neighbourhoods by price) against a pandas groupby on the same data | Rewrote query 3's tenure bucket CASE statement — first version miscounted the boundary years |
| 2026-07-11 | Claude Code (Sonnet) | Pipeline metadata layer + incremental load | "Add stage-level metadata tracking, error handling, and upsert-based incremental loading" | Ran full pipeline twice in a row; confirmed second run's row_count_out matched, and re-running didn't duplicate fact table rows | None |