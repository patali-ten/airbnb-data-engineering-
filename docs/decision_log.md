# Decision Log

### 2026-07-09 — City selection
**Options considered:** NYC, London, Edinburgh, Bangkok
**Decision:** Edinburgh
**Why:** Manageable dataset size for a solo 4-day timeline; strong seasonal story (Fringe Festival) adds analytical depth without multi-city complexity.
**Trade-off accepted:** Smaller market = less impressive absolute scale, but higher-quality single-city analysis scores better per the brief's own guidance.

### 2026-07-09 — listings.csv vs listings.csv (detailed)
**Options considered:** Use the "detailed" file (full descriptions/metadata) or the summary listings.csv
**Decision:** Summary listings.csv
**Why:** Detailed file adds free-text description fields not needed for pricing/EDA/stats work; keeps processing faster given time constraints.
**Trade-off accepted:** Lose raw description text — acceptable since NLP-on-descriptions is an optional Section 7 task we're deprioritizing anyway.

## Assumptions

### 2026-07-10 — Handling fully-null and high-null columns
**Observation:** Several columns are 100% null in listings.csv: neighborhood_overview, host_since, 
host_response_time, host_response_rate, host_acceptance_rate, host_thumbnail_url, host_neighbourhood, 
host_total_listings_count, host_verifications, neighbourhood, neighbourhood_group_cleansed, 
calendar_updated, instant_bookable.
**Decision:** Treat these as unavailable-in-this-scrape rather than data quality errors, and drop them 
from downstream analysis rather than attempting imputation.
**Why:** A 100% null rate across tens of thousands of rows indicates the field was deprecated or 
withheld at scrape time (e.g. Airbnb no longer exposes host_response_rate publicly), not a random 
missingness pattern we could reasonably impute.

### 2026-07-10 — bedrooms / beds / bathrooms missingness
**Observation:** bedrooms is missing in 20.74% of listings, beds in 16.72%, bathrooms in 22.33%.
**Decision:** Assume missing bedrooms = studio (1 room, sleeping/living combined) when accommodates <= 2, 
and flag (not impute) missing bedrooms when accommodates > 2, since a multi-person listing with no 
bedroom count is a genuine data gap, not a studio.
**Trade-off accepted:** This introduces an assumption-driven fill for the studio case; we document it 
rather than silently imputing, so any price/bedroom correlation analysis downstream can be re-run 
excluding assumed values as a sensitivity check.

### 2026-07-10 — license field interpretation
**Observation:** license is missing in 70.15% of listings; where present, values look like short-term 
let licence numbers (e.g. EH-68481-F).
**Decision:** Treat missing license as "not yet licensed / unknown" rather than "illegally operating," 
since Edinburgh's STL licensing scheme phased in gradually and Inside Airbnb's field reflects what 
hosts self-report, not verified regulatory status.
**Why:** Conflating missing license with non-compliance would overstate illegal-listing claims the data 
can't actually support.

### 2026-07-10 — price missingness (10.15%) and price_quote_* fields
**Observation:** price is missing in 10.15% of listings, but price_quote_price_per_night and 
price_quote_total_price are also missing at the same 10.15% rate.
**Decision:** Treat this as listings with no live availability quote at scrape time (e.g. fully booked 
or blocked calendars), not as unpriced/free listings.
**Why:** The identical missing rate across price and price_quote_* fields suggests they're computed 
together from the same live-quote step, which fails together rather than independently — consistent 
with an availability-dependent quote process, not random data loss.

### 2026-07-10 — Missing review scores
**Options considered:** Impute with global mean, impute with 0, leave as explicit null
**Decision:** Leave as explicit null
**Why:** A missing review score means "no reviews yet," not "bad reviews." Imputing a value would misrepresent brand-new listings as average performers.
**Trade-off accepted:** Downstream aggregate stats (e.g. avg review score by neighbourhood) must explicitly handle nulls, not silently drop rows.

### 2026-07-10 — Revenue estimation methodology
**Options considered:** No revenue estimate (data doesn't include real bookings); proxy via unavailable-days × price
**Decision:** Proxy via unavailable-days × price, clearly labeled as an estimate
**Why:** Inside Airbnb's own methodology notes availability ≠ confirmed bookings; a blocked date could mean owner-block, not a booking. This is the best available proxy without real transaction data.
**Trade-off accepted:** Revenue figures are directional, not precise — this must be stated as a limitation everywhere the figure is used.

### 2026-07-10 — Incremental processing strategy
**Options considered:** Full drop-and-reload on every run; true CDC with timestamp-based diffing; upsert on primary key
**Decision:** Upsert (INSERT OR REPLACE) keyed on listing_id
**Why:** Simplest approach that genuinely avoids full reprocessing, appropriate for the scale and timeframe of this project.
**Trade-off accepted:** Doesn't capture deletions (delisted properties) or field-level change history — a production system would want a proper SCD Type 2 dimension or CDC log, noted in Future Improvements.