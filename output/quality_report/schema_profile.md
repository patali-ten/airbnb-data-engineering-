# Schema Profile: edinburgh
Generated: 2026-07-10 13:35:35

## calendar.csv
Rows: 2284170 | Columns: 5

| Column | Dtype | Null Rate | Cardinality | Min | Max | Sample Values |
|---|---|---|---|---|---|---|
| listing_id | int64 | 0.00% | 6258 | 15420 | 1713410170953742690 | `15420`, `24288`, `38628` |
| date | str | 0.00% | 374 | — | — | `2026-07-02`, `2026-07-03`, `2026-07-04` |
| available | str | 0.00% | 2 | — | — | `f`, `t` |
| minimum_nights | int64 | 0.00% | 61 | 1 | 999 | `3`, `4`, `2` |
| maximum_nights | int64 | 0.00% | 379 | 1 | 1125 | `30`, `1125`, `60` |

## listings.csv
Rows: 6244 | Columns: 90

| Column | Dtype | Null Rate | Cardinality | Min | Max | Sample Values |
|---|---|---|---|---|---|---|
| id | int64 | 0.00% | 6244 | 15420 | 1713410170953742690 | `15420`, `24288`, `38628` |
| listing_url | str | 0.00% | 6244 | — | — | `https://www.airbnb.com/rooms/15420`, `https://www.airbnb.com/rooms/24288`, `https://www.airbnb.com/rooms/38628` |
| scrape_id | int64 | 0.00% | 1 | 20260623040725 | 20260623040725 | `20260623040725` |
| last_scraped | str | 0.00% | 2 | — | — | `2026-07-02`, `2026-06-23` |
| source | str | 0.00% | 2 | — | — | `previous scrape`, `city scrape` |
| name | str | 0.00% | 6127 | — | — | `Georgian Boutique Apt City Centre`, `Cool central Loft, sleeps 4, 2 double...`, `Edinburgh Holiday Let` |
| description | str | 1.22% | 5758 | — | — | `Stunning, spacious ground floor apart...`, `Upper level of duplex. Boho rustic-ch...`, `Self contained studio 6 minutes by tr...` |
| neighborhood_overview | float64 | 100.00% | 0 | — | — | — |
| picture_url | str | 0.14% | 6174 | — | — | `https://a0.muscache.com/pictures/cf69...`, `https://a0.muscache.com/pictures/3460...`, `https://a0.muscache.com/pictures/host...` |
| host_id | int64 | 0.00% | 3669 | 2784 | 1713184274972947470 | `60423`, `46498`, `165635` |
| host_url | str | 0.00% | 3669 | — | — | `https://www.airbnb.com/users/show/60423`, `https://www.airbnb.com/users/show/46498`, `https://www.airbnb.com/users/show/165635` |
| host_profile_id | float64 | 0.10% | 3668 | 1462506322856848128 | 1713184919440878848 | `1.4625079731021545e+18`, `1.4625075663867292e+18`, `1.4625114716340925e+18` |
| host_profile_url | str | 0.02% | 3669 | — | — | `https://www.airbnb.com/users/profile/...`, `https://www.airbnb.com/users/profile/...`, `https://www.airbnb.com/users/profile/...` |
| host_name | str | 0.10% | 1762 | — | — | `Charlotte`, `Gordon`, `Trish` |
| host_since | float64 | 100.00% | 0 | — | — | — |
| hosts_time_as_user_years | float64 | 0.10% | 18 | 0 | 17 | `16.0`, `15.0`, `9.0` |
| hosts_time_as_user_months | float64 | 0.10% | 12 | 0 | 11 | `6.0`, `8.0`, `11.0` |
| hosts_time_as_host_years | float64 | 0.10% | 16 | 0 | 15 | `15.0`, `14.0`, `9.0` |
| hosts_time_as_host_months | float64 | 0.10% | 12 | 0 | 11 | `6.0`, `5.0`, `2.0` |
| host_location | str | 20.32% | 189 | — | — | `Edinburgh, United Kingdom`, `London, United Kingdom`, `Galashiels, United Kingdom` |
| host_about | str | 43.43% | 1819 | — | — | `I have a background in property, havi...`, `Principal Studio DuB Architecture & P...`, `Hi   I like travelling and housing pr...` |
| host_response_time | float64 | 100.00% | 0 | — | — | — |
| host_response_rate | float64 | 100.00% | 0 | — | — | — |
| host_acceptance_rate | float64 | 100.00% | 0 | — | — | — |
| host_is_superhost | str | 0.10% | 2 | — | — | `t`, `f` |
| host_thumbnail_url | float64 | 100.00% | 0 | — | — | — |
| host_picture_url | str | 0.10% | 3588 | — | — | `https://a0.muscache.com/im/users/6042...`, `https://a0.muscache.com/im/users/4649...`, `https://a0.muscache.com/im/users/1656...` |
| host_neighbourhood | float64 | 100.00% | 0 | — | — | — |
| host_listings_count | float64 | 0.10% | 70 | 0 | 2550 | `1.0`, `16.0`, `3.0` |
| host_total_listings_count | float64 | 100.00% | 0 | — | — | — |
| host_verifications | float64 | 100.00% | 0 | — | — | — |
| host_has_profile_pic | str | 0.10% | 2 | — | — | `t`, `f` |
| host_identity_verified | str | 0.10% | 2 | — | — | `t`, `f` |
| neighbourhood | float64 | 100.00% | 0 | — | — | — |
| neighbourhood_cleansed | str | 0.00% | 111 | — | — | `Old Town, Princes Street and Leith St...`, `Canongate, Southside and Dumbiedykes`, `Joppa` |
| neighbourhood_group_cleansed | float64 | 100.00% | 0 | — | — | — |
| latitude | float64 | 0.00% | 4952 | 55.86 | 55.99 | `55.95759`, `55.94498320836646`, `55.94215` |
| longitude | float64 | 0.00% | 5380 | -3.44 | -3.08 | `-3.18805`, `-3.185293348616568`, `-3.0964` |
| property_type | str | 0.00% | 53 | — | — | `Entire rental unit`, `Entire loft`, `Private room in condo` |
| room_type | str | 0.00% | 4 | — | — | `Entire home/apt`, `Private room`, `Hotel room` |
| accommodates | int64 | 0.00% | 16 | 1 | 16 | `2`, `4`, `3` |
| bathrooms | float64 | 22.33% | 16 | 0.50 | 9 | `1.5`, `1.0`, `2.0` |
| bathrooms_text | str | 0.80% | 27 | — | — | `1 bath`, `1.5 baths`, `1 private bath` |
| bedrooms | float64 | 20.74% | 11 | 1 | 12 | `1.0`, `2.0`, `3.0` |
| beds | float64 | 16.72% | 19 | 1 | 20 | `2.0`, `3.0`, `1.0` |
| amenities | str | 0.00% | 5976 | — | — | `["Sound system", "Bed linens", "Singl...`, `["Paid parking off premises", "Wifi",...`, `["Window guards", "Washer", "Wifi", "...` |
| price | str | 10.15% | 1988 | — | — | `$225.50`, `$202.00`, `$128.75` |
| price_quote_checkin_date | str | 7.69% | 213 | — | — | `2026-10-26`, `2026-10-11`, `2026-07-20` |
| price_quote_checkout_date | str | 7.69% | 238 | — | — | `2026-10-28`, `2026-10-14`, `2026-07-24` |
| price_quote_total_price | float64 | 10.15% | 1846 | 20 | 290690.31 | `451.0`, `606.0`, `515.0` |
| price_quote_price_per_night | float64 | 10.15% | 1988 | 4.78 | 12042.29 | `225.5`, `202.0`, `128.75` |
| price_quote_raw | str | 7.69% | 5463 | — | — | `{"quote": {"taxes": null, "currency":...`, `{"quote": {"taxes": null, "currency":...`, `{"quote": {"taxes": null, "currency":...` |
| minimum_nights | float64 | 0.03% | 37 | 1 | 365 | `2.0`, `3.0`, `1.0` |
| maximum_nights | float64 | 0.03% | 100 | 1 | 1125 | `30.0`, `1125.0`, `60.0` |
| minimum_minimum_nights | float64 | 0.03% | 37 | 1 | 365 | `2.0`, `3.0`, `1.0` |
| maximum_minimum_nights | float64 | 0.03% | 52 | 1 | 999 | `4.0`, `3.0`, `6.0` |
| minimum_maximum_nights | float64 | 0.03% | 93 | 1 | 1125 | `30.0`, `1125.0`, `60.0` |
| maximum_maximum_nights | float64 | 0.03% | 100 | 1 | 1125 | `30.0`, `1125.0`, `60.0` |
| minimum_nights_avg_ntm | float64 | 0.00% | 199 | 1 | 522.30 | `3.0`, `4.0`, `2.0` |
| maximum_nights_avg_ntm | float64 | 0.00% | 497 | 1 | 1125 | `30.0`, `1125.0`, `60.0` |
| calendar_updated | float64 | 100.00% | 0 | — | — | — |
| has_availability | str | 0.18% | 2 | — | — | `t`, `f` |
| availability_30 | int64 | 0.00% | 31 | 0 | 30 | `0`, `5`, `3` |
| availability_60 | int64 | 0.00% | 61 | 0 | 60 | `1`, `7`, `4` |
| availability_90 | int64 | 0.00% | 91 | 0 | 90 | `4`, `10`, `8` |
| availability_365 | int64 | 0.00% | 366 | 0 | 365 | `28`, `176`, `258` |
| calendar_last_scraped | str | 0.00% | 2 | — | — | `2026-07-02`, `2026-06-23` |
| number_of_reviews | int64 | 0.00% | 630 | 0 | 1773 | `704`, `433`, `76` |
| number_of_reviews_ltm | int64 | 0.00% | 135 | 0 | 291 | `73`, `46`, `1` |
| number_of_reviews_l30d | int64 | 0.00% | 22 | 0 | 21 | `6`, `1`, `5` |
| availability_eoy | int64 | 0.00% | 193 | 0 | 192 | `26`, `46`, `87` |
| number_of_reviews_ly | int64 | 0.00% | 135 | 0 | 355 | `67`, `53`, `0` |
| estimated_occupancy_l365d | int64 | 0.00% | 75 | 0 | 255 | `255`, `6`, `210` |
| estimated_revenue_l365d | float64 | 10.15% | 3454 | 0 | 1388004 | `57503.0`, `51510.0`, `773.0` |
| first_review | str | 10.59% | 2335 | — | — | `2011-01-18`, `2010-09-19`, `2014-06-13` |
| last_review | str | 10.59% | 582 | — | — | `2026-06-28`, `2026-06-07`, `2026-05-25` |
| review_scores_rating | float64 | 10.59% | 122 | 1 | 5 | `4.98`, `4.66`, `4.68` |
| review_scores_accuracy | float64 | 10.59% | 112 | 1 | 5 | `4.99`, `4.82`, `4.78` |
| review_scores_cleanliness | float64 | 10.59% | 126 | 1 | 5 | `4.97`, `4.39`, `4.66` |
| review_scores_checkin | float64 | 10.59% | 117 | 1 | 5 | `4.98`, `4.88`, `4.83` |
| review_scores_communication | float64 | 10.59% | 99 | 1 | 5 | `4.99`, `4.92`, `4.78` |
| review_scores_location | float64 | 10.59% | 115 | 1 | 5 | `4.98`, `4.86`, `4.72` |
| review_scores_value | float64 | 10.59% | 134 | 1 | 5 | `4.92`, `4.68`, `4.75` |
| license | str | 70.15% | 1700 | — | — | `EH-68481-F`, `EH-70886-F`, `EH-70355-F` |
| instant_bookable | float64 | 100.00% | 0 | — | — | — |
| calculated_host_listings_count | int64 | 0.00% | 34 | 1 | 116 | `1`, `12`, `3` |
| calculated_host_listings_count_entire_homes | int64 | 0.00% | 32 | 0 | 102 | `1`, `0`, `12` |
| calculated_host_listings_count_private_rooms | int64 | 0.00% | 15 | 0 | 19 | `0`, `1`, `2` |
| calculated_host_listings_count_shared_rooms | int64 | 0.00% | 5 | 0 | 8 | `0`, `6`, `5` |
| reviews_per_month | float64 | 10.59% | 806 | 0.01 | 22.26 | `3.74`, `2.26`, `0.52` |

## neighbourhoods.csv
Rows: 111 | Columns: 2

| Column | Dtype | Null Rate | Cardinality | Min | Max | Sample Values |
|---|---|---|---|---|---|---|
| neighbourhood_group | float64 | 100.00% | 0 | — | — | — |
| neighbourhood | str | 0.00% | 111 | — | — | `Abbeyhill`, `Baberton and Juniper Green`, `Balerno and Bonnington Village` |

## reviews.csv
Rows: 676263 | Columns: 6

| Column | Dtype | Null Rate | Cardinality | Min | Max | Sample Values |
|---|---|---|---|---|---|---|
| listing_id | int64 | 0.00% | 5590 | 15420 | 1709702515932532399 | `15420`, `24288`, `38628` |
| id | int64 | 0.00% | 676263 | 100198 | 1721093843062856959 | `171793`, `176350`, `232149` |
| date | str | 0.00% | 5249 | — | — | `2011-01-18`, `2011-01-31`, `2011-04-19` |
| reviewer_id | int64 | 0.00% | 629220 | 46 | 1711461837171804166 | `186358`, `95218`, `429751` |
| reviewer_name | str | 0.00% | 82054 | — | — | `Nels`, `Gareth`, `Guido` |
| comments | str | 0.01% | 661041 | — | — | `My wife and I stayed at this beautifu...`, `Charlotte couldn't have been a more t...`, `I went to Edinburgh for the second ti...` |

## Data Quality Checks

### Missing Value Rates (listings.csv)

| Field | Total Records | Missing Count | Missing % |
|---|---|---|---|
| review_scores_rating | 6244 | 661 | 10.59% |
| bedrooms | 6244 | 1295 | 20.74% |
| beds | 6244 | 1044 | 16.72% |

### calendar.csv

- `price` column not present in calendar.csv (2284170 rows total).
- calendar.csv covers 2026-06-23 to 2027-07-01 (374 unique dates).

## Referential Integrity

| Check | Total Records | Orphaned/Duplicate | Percentage |
|---|---|---|---|
| listings.csv: id uniqueness | 6244 | 0 | 0.00% |
| calendar.csv: listing_id found in listings.csv | 2284170 | 5110 | 0.22% |
| reviews.csv: listing_id found in listings.csv | 676263 | 642 | 0.09% |
| listings.csv: neighbourhood_cleansed found in neighbourhoods.csv | 6244 | 0 | 0.00% |
