-- SQL Query for analyzing price volatility
-- Calculates standard deviation and other volatility metrics

WITH price_data AS (
    SELECT 
        p.id AS product_id,
        p.name AS product_name,
        p.current_price,
        pp.price,
        pp.timestamp,
        LAG(pp.price) OVER (PARTITION BY p.id ORDER BY pp.timestamp) AS prev_price,
        ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY pp.timestamp DESC) AS row_num
    FROM 
        products_productprice pp
    JOIN 
        products_product p ON pp.product_id = p.id
    WHERE 
        pp.timestamp >= NOW() - INTERVAL '90 days'
        AND p.id = %(product_id)s
),
daily_changes AS (
    SELECT 
        product_id,
        product_name,
        timestamp::date AS date,
        AVG(price) AS avg_price,
        MAX(price) AS max_price,
        MIN(price) AS min_price,
        MAX(price) - MIN(price) AS daily_range,
        CASE 
            WHEN AVG(price) = 0 THEN 0
            ELSE (MAX(price) - MIN(price)) / AVG(price) * 100 
        END AS daily_range_pct
    FROM 
        price_data
    GROUP BY 
        product_id, product_name, timestamp::date
),
volatility_metrics AS (
    SELECT
        product_id,
        product_name,
        COUNT(DISTINCT date) AS days_with_data,
        AVG(avg_price) AS period_avg_price,
        STDDEV(avg_price) AS price_stddev,
        AVG(daily_range) AS avg_daily_range,
        AVG(daily_range_pct) AS avg_daily_range_pct,
        CASE 
            WHEN AVG(avg_price) = 0 THEN 0
            ELSE STDDEV(avg_price) / AVG(avg_price) * 100 
        END AS coefficient_of_variation
    FROM 
        daily_changes
    GROUP BY 
        product_id, product_name
)
SELECT 
    vm.*,
    (SELECT price FROM price_data WHERE row_num = 1) AS latest_price,
    (SELECT current_price FROM price_data LIMIT 1) AS current_system_price
FROM 
    volatility_metrics vm;
