-- AcmeCloud Phase 0 schema.
--
-- This database belongs to the simulated AcmeCloud environment.
-- It is intentionally separate from the future OpsPilot operational
-- database. The latter will be introduced when we build the platform
-- layer.

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    status VARCHAR(32) NOT NULL,
    total_amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id
    ON orders (customer_id);

CREATE INDEX IF NOT EXISTS idx_orders_created_at
    ON orders (created_at);
