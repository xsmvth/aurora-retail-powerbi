-- Optional PostgreSQL schema for Power BI Service scheduled refresh.
-- The SQLite warehouse is the local source of truth. The ETL can synchronize
-- the exported star-schema tables to this database when DATABASE_URL is set.

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month_number INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    month_short TEXT NOT NULL,
    month_start DATE NOT NULL,
    month_key TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    weekday_name TEXT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE OR REPLACE VIEW dim_month AS
SELECT DISTINCT
    month_key,
    month_start,
    year,
    month_number,
    month_name,
    month_short
FROM dim_date;

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    segment TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT NOT NULL,
    signup_date DATE NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_key TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    list_price NUMERIC(12, 2) NOT NULL,
    unit_cost NUMERIC(12, 2) NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_store (
    store_key TEXT PRIMARY KEY,
    store_name TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT NOT NULL,
    store_type TEXT NOT NULL,
    opening_date DATE NOT NULL
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
    unit_price NUMERIC(12, 2) NOT NULL,
    discount_pct NUMERIC(6, 4) NOT NULL,
    revenue NUMERIC(14, 2) NOT NULL,
    cost NUMERIC(14, 2) NOT NULL,
    gross_profit NUMERIC(14, 2) NOT NULL,
    is_return BOOLEAN NOT NULL,
    payment_method TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_fact_sales_date ON fact_sales(date_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_product ON fact_sales(product_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_store ON fact_sales(store_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_channel ON fact_sales(channel_key);

CREATE TABLE IF NOT EXISTS fact_targets (
    target_month TEXT NOT NULL,
    store_key TEXT NOT NULL REFERENCES dim_store(store_key),
    channel_key TEXT NOT NULL REFERENCES dim_channel(channel_key),
    target_revenue NUMERIC(14, 2) NOT NULL,
    PRIMARY KEY (target_month, store_key, channel_key)
);
