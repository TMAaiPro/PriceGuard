-- SQL Query for generating insights from product data
-- Analyzes optimal purchase timing and competitor pricing

WITH seasonal_data AS (
    SELECT 
        EXTRACT(MONTH FROM pp.timestamp) AS month,
        p.id AS product_id,
        p.name AS product_name,
        AVG(pp.price) AS avg_monthly_price
    FROM 
        products_productprice pp
    JOIN 
        products_product p ON pp.product_id = p.id
    WHERE 
        pp.timestamp >= NOW() - INTERVAL '1 year'
        AND p.id = %(product_id)s
    GROUP BY 
        EXTRACT(MONTH FROM pp.timestamp), p.id, p.name
),
month_ranking AS (
    SELECT 
        month,
        product_id,
        product_name,
        avg_monthly_price,
        RANK() OVER (PARTITION BY product_id ORDER BY avg_monthly_price) AS price_rank
    FROM 
        seasonal_data
),
price_history AS (
    SELECT 
        p.id AS product_id,
        p.name AS product_name,
        MIN(pp.price) AS historical_min,
        MAX(pp.price) AS historical_max,
        AVG(pp.price) AS historical_avg,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY pp.price) AS percentile_25,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY pp.price) AS percentile_50,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY pp.price) AS percentile_75
    FROM 
        products_productprice pp
    JOIN 
        products_product p ON pp.product_id = p.id
    WHERE 
        p.id = %(product_id)s
    GROUP BY 
        p.id, p.name
),
competitor_analysis AS (
    SELECT 
        p1.id AS product_id,
        p1.name AS product_name,
        p1.current_price,
        r1.name AS retailer,
        p2.id AS competitor_id,
        p2.name AS competitor_name,
        p2.current_price AS competitor_price,
        r2.name AS competitor_retailer,
        p1.current_price - p2.current_price AS price_difference,
        CASE WHEN p2.current_price = 0 THEN 0 
             ELSE ((p1.current_price - p2.current_price) / p2.current_price) * 100 
        END AS price_difference_pct
    FROM 
        products_product p1
    JOIN 
        products_retailer r1 ON p1.retailer_id = r1.id
    JOIN 
        products_product p2 ON p1.id <> p2.id
    JOIN 
        products_retailer r2 ON p2.retailer_id = r2.id
    JOIN 
        products_product_categories pc1 ON p1.id = pc1.product_id
    JOIN 
        products_product_categories pc2 ON p2.id = pc2.product_id
    WHERE 
        p1.id = %(product_id)s
        AND pc1.category_id = pc2.category_id
)
SELECT 
    ph.*,
    (SELECT month FROM month_ranking WHERE price_rank = 1 LIMIT 1) AS best_month_to_buy,
    (SELECT avg_monthly_price FROM month_ranking WHERE price_rank = 1 LIMIT 1) AS best_month_avg_price,
    (SELECT COUNT(*) FROM competitor_analysis WHERE price_difference < 0) AS cheaper_competitors,
    (SELECT COUNT(*) FROM competitor_analysis WHERE price_difference > 0) AS more_expensive_competitors,
    (SELECT MIN(competitor_price) FROM competitor_analysis) AS cheapest_competitor_price,
    (SELECT competitor_name FROM competitor_analysis ORDER BY competitor_price ASC LIMIT 1) AS cheapest_competitor,
    (SELECT competitor_retailer FROM competitor_analysis ORDER BY competitor_price ASC LIMIT 1) AS cheapest_competitor_retailer
FROM 
    price_history ph;
