# Analytical Query Results: edinburgh

## Top 10 neighbourhoods by median price

```sql
SELECT neighbourhood, median_price, listing_density, avg_rating
        FROM dim_neighbourhood
        ORDER BY median_price DESC
        LIMIT 10;
```

| neighbourhood | median_price | listing_density | avg_rating |
|---|---|---|---|
| Fairmilehead | 359.50 | 2 | 4.91 |
| Marchmont West | 341.00 | 56 | 4.84 |
| New Town West | 337.33 | 222 | 4.82 |
| New Town East and Gayfield | 292.50 | 174 | 4.80 |
| Old Town, Princes Street and Leith Street | 288.15 | 747 | 4.75 |
| Canongate, Southside and Dumbiedykes | 286.00 | 204 | 4.74 |
| Barnton, Cammo and Cramond South | 283.25 | 2 | 4.86 |
| Merchiston and Greenhill | 279.00 | 35 | 4.82 |
| Tollcross | 274.50 | 341 | 4.72 |
| Stockbridge | 272.30 | 130 | 4.86 |

## Superhost vs non-superhost: avg occupancy and revenue

```sql
SELECT
            CASE WHEN h.host_is_superhost = 't' THEN 'Superhost' ELSE 'Non-superhost' END AS host_type,
            COUNT(*) AS listing_count,
            AVG(f.occupancy_rate_365) AS avg_occupancy_rate,
            AVG(f.estimated_annual_revenue) AS avg_estimated_annual_revenue
        FROM fact_listing_performance f
        JOIN dim_host h ON f.host_id = h.host_id
        WHERE h.host_is_superhost IS NOT NULL
        GROUP BY host_type;
```

| host_type | listing_count | avg_occupancy_rate | avg_estimated_annual_revenue |
|---|---|---|---|
| Non-superhost | 3281 | 0.57 | 57215.42 |
| Superhost | 2957 | 0.66 | 63547.53 |

## Avg review score by host tenure bucket

```sql
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
```

| tenure_bucket | listing_count | avg_review_score |
|---|---|---|
| Unknown | 6244 | 4.78 |

## Avg estimated annual revenue by room_type

```sql
SELECT
            room_type,
            COUNT(*) AS listing_count,
            AVG(estimated_annual_revenue) AS avg_estimated_annual_revenue
        FROM fact_listing_performance
        GROUP BY room_type
        ORDER BY avg_estimated_annual_revenue DESC;
```

| room_type | listing_count | avg_estimated_annual_revenue |
|---|---|---|
| entire home/apt | 4445 | 70860.47 |
| private room | 1752 | 34218.59 |
| hotel room | 26 | 33719.20 |
| shared room | 21 | 7709.06 |
