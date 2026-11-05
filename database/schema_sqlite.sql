PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month_number INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    month_short TEXT NOT NULL,
    month_start TEXT NOT NULL,
    month_key TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    weekday_name TEXT NOT NULL,
    is_weekend INTEGER NOT NULL CHECK (is_weekend IN (0, 1))
);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    segment TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT NOT NULL,
    signup_date TEXT NOT NULL,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_key TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    list_price REAL NOT NULL CHECK (list_price >= 0),
    unit_cost REAL NOT NULL CHECK (unit_cost >= 0),
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS dim_store (
    store_key TEXT PRIMARY KEY,
    store_name TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT NOT NULL,
    store_type TEXT NOT NULL,
    opening_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_channel (
    channel_key TEXT PRIMARY KEY,
    channel_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_sales (
    sale_line_key TEXT PRIMARY KEY,
    order_key TEXT NOT NULL,
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    customer_key TEXT NOT NULL REFERENCES dim_customer(customer_key),
    product_key TEXT NOT NULL REFERENCES dim_product(product_key),
    store_key TEXT NOT NULL REFERENCES dim_store(store_key),
    channel_key TEXT NOT NULL REFERENCES dim_channel(channel_key),
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    discount_pct REAL NOT NULL CHECK (discount_pct BETWEEN 0 AND 0.95),
    revenue REAL NOT NULL,
    cost REAL NOT NULL,
    gross_profit REAL NOT NULL,
    is_return INTEGER NOT NULL CHECK (is_return IN (0, 1)),
    payment_method TEXT NOT NULL,
    loaded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_fact_sales_date ON fact_sales(date_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_product ON fact_sales(product_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_store ON fact_sales(store_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_channel ON fact_sales(channel_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_order ON fact_sales(order_key);

CREATE TABLE IF NOT EXISTS fact_targets (
    target_month TEXT NOT NULL,
    store_key TEXT NOT NULL REFERENCES dim_store(store_key),
    channel_key TEXT NOT NULL REFERENCES dim_channel(channel_key),
    target_revenue REAL NOT NULL CHECK (target_revenue >= 0),
    PRIMARY KEY (target_month, store_key, channel_key)
);

CREATE TABLE IF NOT EXISTS etl_file_registry (
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    processed_at TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (file_name, file_hash)
);

CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    sale_rows_seen INTEGER DEFAULT 0,
    rows_rejected INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    message TEXT
);

DROP VIEW IF EXISTS dim_month;
CREATE VIEW dim_month AS
SELECT DISTINCT
    month_key,
    month_start,
    year,
    month_number,
    month_name,
    month_short
FROM dim_date;

DROP VIEW IF EXISTS vw_sales_enriched;
CREATE VIEW vw_sales_enriched AS
SELECT
    f.sale_line_key,
    f.order_key,
    f.customer_key,
    f.product_key,
    f.store_key,
    f.channel_key,
    d.date,
    d.year,
    d.quarter,
    d.month_number,
    d.month_start,
    c.segment AS customer_segment,
    c.region AS customer_region,
    p.category,
    p.subcategory,
    s.store_name,
    s.region AS store_region,
    ch.channel_name,
    f.quantity,
    f.unit_price,
    f.discount_pct,
    f.revenue,
    f.cost,
    f.gross_profit,
    f.is_return,
    f.payment_method
FROM fact_sales AS f
JOIN dim_date AS d ON d.date_key = f.date_key
JOIN dim_customer AS c ON c.customer_key = f.customer_key
JOIN dim_product AS p ON p.product_key = f.product_key
JOIN dim_store AS s ON s.store_key = f.store_key
JOIN dim_channel AS ch ON ch.channel_key = f.channel_key;

DROP VIEW IF EXISTS vw_monthly_kpis;
CREATE VIEW vw_monthly_kpis AS
SELECT
    month_start,
    ROUND(SUM(revenue), 2) AS revenue,
    ROUND(SUM(cost), 2) AS cost,
    ROUND(SUM(gross_profit), 2) AS gross_profit,
    ROUND(100.0 * SUM(gross_profit) / NULLIF(SUM(revenue), 0), 2) AS margin_pct,
    COUNT(DISTINCT order_key) AS orders,
    ROUND(SUM(revenue) / NULLIF(COUNT(DISTINCT order_key), 0), 2) AS average_ticket,
    COUNT(DISTINCT customer_key) AS active_customers
FROM vw_sales_enriched
GROUP BY month_start;

DROP VIEW IF EXISTS vw_store_performance;
CREATE VIEW vw_store_performance AS
SELECT
    store_name,
    store_region,
    ROUND(SUM(revenue), 2) AS revenue,
    ROUND(SUM(gross_profit), 2) AS gross_profit,
    ROUND(100.0 * SUM(gross_profit) / NULLIF(SUM(revenue), 0), 2) AS margin_pct,
    COUNT(DISTINCT order_key) AS orders,
    COUNT(DISTINCT customer_key) AS active_customers
FROM vw_sales_enriched
GROUP BY store_name, store_region;

DROP VIEW IF EXISTS vw_category_performance;
CREATE VIEW vw_category_performance AS
SELECT
    category,
    ROUND(SUM(revenue), 2) AS revenue,
    ROUND(SUM(gross_profit), 2) AS gross_profit,
    ROUND(100.0 * SUM(gross_profit) / NULLIF(SUM(revenue), 0), 2) AS margin_pct,
    SUM(CASE WHEN is_return = 0 THEN quantity ELSE 0 END) AS units_sold
FROM vw_sales_enriched
GROUP BY category;
