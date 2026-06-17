-- ============================================================================
-- OkCredit — Supabase PostgreSQL Schema
-- Multi-Tenant SaaS Architecture
-- ============================================================================
-- HOW TO USE:
--   1. Go to https://supabase.com → your project → SQL Editor
--   2. Paste this entire script and click RUN
--   3. All tables will be created (or safely migrated if they exist)
--   4. Then paste your db_url into .streamlit/secrets.toml and restart the app
-- ============================================================================

-- ── Users / Auth ──────────────────────────────────────────────────────────────
-- owner_id is NULL for owner accounts; for worker accounts it points to the
-- owning user's id (i.e. the business owner they work for).
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'worker',
    full_name   TEXT,
    owner_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Customers (retailers) ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    id              SERIAL PRIMARY KEY,
    owner_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_name   TEXT NOT NULL,
    contact_person  TEXT,
    phone           TEXT,
    address         TEXT,
    credit_limit    REAL DEFAULT 0.0,
    current_balance REAL DEFAULT 0.0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Inventory ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inventory (
    id              SERIAL PRIMARY KEY,
    owner_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sku             TEXT NOT NULL,
    name            TEXT NOT NULL,
    category        TEXT,
    quantity        INTEGER DEFAULT 0,
    unit            TEXT DEFAULT 'pcs',
    price           REAL NOT NULL,
    cost            REAL NOT NULL,
    min_stock_level INTEGER DEFAULT 10,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (owner_id, sku)
);

-- ── Orders ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id             SERIAL PRIMARY KEY,
    owner_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    customer_id    INTEGER REFERENCES customers(id),
    order_date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status         TEXT DEFAULT 'Pending',
    total_amount   REAL DEFAULT 0.0,
    payment_status TEXT DEFAULT 'Unpaid'
);

-- ── Order Items ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_items (
    id             SERIAL PRIMARY KEY,
    order_id       INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    item_id        INTEGER REFERENCES inventory(id),
    quantity       INTEGER NOT NULL,
    price_at_order REAL NOT NULL
);

-- ── Workers ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workers (
    id          SERIAL PRIMARY KEY,
    owner_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL,
    status      TEXT DEFAULT 'Active',
    phone       TEXT,
    worker_code TEXT UNIQUE,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- ── Deliveries ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS deliveries (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    worker_id       INTEGER REFERENCES workers(id) ON DELETE SET NULL,
    delivery_status TEXT DEFAULT 'Scheduled',
    delivery_date   TIMESTAMP,
    notes           TEXT
);

-- ── Payment History ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payment_history (
    id           SERIAL PRIMARY KEY,
    order_id     INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    delivery_id  INTEGER REFERENCES deliveries(id) ON DELETE SET NULL,
    worker_id    INTEGER REFERENCES workers(id) ON DELETE SET NULL,
    amount       REAL NOT NULL DEFAULT 0.0,
    payment_mode TEXT DEFAULT 'Cash',
    outcome      TEXT DEFAULT 'full',
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes        TEXT
);

-- ── Performance Indexes ───────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_customers_owner    ON customers(owner_id);
CREATE INDEX IF NOT EXISTS idx_inventory_owner    ON inventory(owner_id);
CREATE INDEX IF NOT EXISTS idx_orders_owner       ON orders(owner_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer    ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order  ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_workers_owner      ON workers(owner_id);
CREATE INDEX IF NOT EXISTS idx_workers_user       ON workers(user_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_order   ON deliveries(order_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_worker  ON deliveries(worker_id);
CREATE INDEX IF NOT EXISTS idx_payment_order      ON payment_history(order_id);
CREATE INDEX IF NOT EXISTS idx_payment_worker     ON payment_history(worker_id);
CREATE INDEX IF NOT EXISTS idx_payment_collected  ON payment_history(collected_at);
CREATE INDEX IF NOT EXISTS idx_users_owner        ON users(owner_id);

-- ============================================================================
-- SAFE MIGRATION: Add owner_id to existing tables (if tables already exist
-- from an older version without owner_id). These are no-ops if column exists.
-- ============================================================================

-- Add owner_id to users if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='users' AND column_name='owner_id'
    ) THEN
        ALTER TABLE users ADD COLUMN owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add owner_id to customers if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='customers' AND column_name='owner_id'
    ) THEN
        ALTER TABLE customers ADD COLUMN owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
        -- Assign existing records to user id=1 (default admin)
        UPDATE customers SET owner_id = (SELECT id FROM users WHERE role='owner' ORDER BY id LIMIT 1)
        WHERE owner_id IS NULL;
    END IF;
END $$;

-- Add owner_id to inventory if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='inventory' AND column_name='owner_id'
    ) THEN
        ALTER TABLE inventory ADD COLUMN owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
        UPDATE inventory SET owner_id = (SELECT id FROM users WHERE role='owner' ORDER BY id LIMIT 1)
        WHERE owner_id IS NULL;
    END IF;
END $$;

-- Add owner_id to orders if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='orders' AND column_name='owner_id'
    ) THEN
        ALTER TABLE orders ADD COLUMN owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
        UPDATE orders SET owner_id = (SELECT id FROM users WHERE role='owner' ORDER BY id LIMIT 1)
        WHERE owner_id IS NULL;
    END IF;
END $$;

-- Add owner_id to workers if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='workers' AND column_name='owner_id'
    ) THEN
        ALTER TABLE workers ADD COLUMN owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
        UPDATE workers SET owner_id = (SELECT id FROM users WHERE role='owner' ORDER BY id LIMIT 1)
        WHERE owner_id IS NULL;
    END IF;
END $$;

-- Add worker_code to workers if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='workers' AND column_name='worker_code'
    ) THEN
        ALTER TABLE workers ADD COLUMN worker_code TEXT UNIQUE;
    END IF;
END $$;

-- ============================================================================
-- DONE. All tables ready for OkCredit multi-tenant SaaS.
-- ============================================================================
