-- SQL Query for analyzing price trends over time
-- Uses TimescaleDB time_bucket function for time-series aggregation

SELECT 
    p.id AS product_id,
    p.name AS product_name,
    r.name AS retailer_name,
    time_bucket('1 day', pp.timestamp) AS day,
    MIN(pp.price) AS min_price,
    MAX(pp.price) AS max_price,
    AVG(pp.price) AS avg_price,
    FIRST(pp.price, pp.timestamp) AS opening_price,
    LAST(pp.price, pp.timestamp) AS closing_price,
    (LAST(pp.price, pp.timestamp) - FIRST(pp.price, pp.timestamp)) AS price_change,
    CASE 
        WHEN FIRST(pp.price, pp.timestamp) = 0 THEN 0
        ELSE ((LAST(pp.price, pp.timestamp) - FIRST(pp.price, pp.timestamp)) / FIRST(pp.price, pp.timestamp)) * 100 
    END AS price_change_percent
FROM 
    products_productprice pp
JOIN 
    products_product p ON pp.product_id = p.id
JOIN 
    products_retailer r ON p.retailer_id = r.id
WHERE 
    pp.timestamp >= NOW() - INTERVAL '30 days'
    AND p.id = %(product_id)s
GROUP BY 
    p.id, p.name, r.name, time_bucket('1 day', pp.timestamp)
ORDER BY 
    day;
