"""
db.py — Database Engine (Multi-Tenant SaaS Edition)
=====================================================
Central module for ALL database operations.

Architecture:
  - Every business table (customers, inventory, orders, workers, deliveries,
    payment_history) has an owner_id column.
  - Every query that touches business data requires an owner_id parameter so
    Owner A never sees Owner B's data.
  - Worker accounts store their owner's user id in users.owner_id.
  - All CRUD functions pass owner_id in WHERE clauses automatically.

Backend selection (via database.py):
  • Supabase PostgreSQL  → .streamlit/secrets.toml [supabase] db_url set
  • Local SQLite         → fallback (wholesale.db)

Both backends are API-compatible via the _PGConn / _SQLiteConn wrappers.

PostgreSQL Compatibility Notes:
  - All ? placeholders are converted to %s automatically by _adapt_sql()
  - All row[0] / row[1] access works via _DictRow (in database.py)
  - DATE() function converted to ::date cast by _adapt_sql()
  - INSERT OR IGNORE converted to ON CONFLICT DO NOTHING by _adapt_sql()
  - INTEGER PRIMARY KEY AUTOINCREMENT converted to SERIAL PRIMARY KEY
  - create_tables() and _run_migrations() only run for SQLite (Supabase
    schema is created separately via supabase_schema.sql)
"""

import hashlib
import os
import string
import random
from datetime import datetime, date
import bcrypt

# ── Database connection (auto-selects PostgreSQL or SQLite) ───────────────────
from database import get_connection, backend_name, is_postgres


# ── Password hashing ──────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Return SHA-256 hash."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# TABLE CREATION  (SQLite only — Supabase uses supabase_schema.sql)
# ─────────────────────────────────────────────────────────────────────────────
def create_tables(conn):
    """
    Create all application tables if they don't already exist.
    Only runs for SQLite. Supabase PostgreSQL schema is managed via
    supabase_schema.sql run in the Supabase SQL Editor.
    """
    cursor = conn.cursor()

    # ── Users / Auth ──────────────────────────────────────────────────────────
    # owner_id = NULL  → this IS an owner account
    # owner_id = <id>  → this is a worker; value = owning user's id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'worker',
            full_name   TEXT,
            owner_id    INTEGER,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Customers (retailers) ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id        INTEGER NOT NULL,
            business_name   TEXT NOT NULL,
            contact_person  TEXT,
            phone           TEXT,
            address         TEXT,
            credit_limit    REAL DEFAULT 0.0,
            current_balance REAL DEFAULT 0.0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Inventory ─────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id        INTEGER NOT NULL,
            sku             TEXT NOT NULL,
            name            TEXT NOT NULL,
            category        TEXT,
            quantity        INTEGER DEFAULT 0,
            unit            TEXT DEFAULT 'pcs',
            price           REAL NOT NULL,
            cost            REAL NOT NULL,
            min_stock_level INTEGER DEFAULT 10,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Orders ────────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id       INTEGER NOT NULL,
            customer_id    INTEGER,
            order_date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status         TEXT DEFAULT 'Pending',
            total_amount   REAL DEFAULT 0.0,
            payment_status TEXT DEFAULT 'Unpaid'
        )
    """)

    # ── Order Items ───────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id       INTEGER,
            item_id        INTEGER,
            quantity       INTEGER NOT NULL,
            price_at_order REAL NOT NULL
        )
    """)

    # ── Workers ───────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id    INTEGER NOT NULL,
            name        TEXT NOT NULL,
            role        TEXT NOT NULL,
            status      TEXT DEFAULT 'Active',
            phone       TEXT,
            worker_code TEXT,
            user_id     INTEGER
        )
    """)

    # ── Deliveries ────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deliveries (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        INTEGER,
            worker_id       INTEGER,
            delivery_status TEXT DEFAULT 'Scheduled',
            delivery_date   TIMESTAMP,
            notes           TEXT
        )
    """)

    # ── Payment History ───────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id     INTEGER,
            delivery_id  INTEGER,
            worker_id    INTEGER,
            amount       REAL NOT NULL DEFAULT 0.0,
            payment_mode TEXT DEFAULT 'Cash',
            outcome      TEXT DEFAULT 'full',
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes        TEXT
        )
    """)

    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# SAFE COLUMN MIGRATIONS  (SQLite only — add columns that may be missing)
# ─────────────────────────────────────────────────────────────────────────────
def _safe_add_column(conn, table: str, column: str, definition: str):
    """Add a column to a table if it does not already exist. No-op otherwise."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        conn.commit()
    except Exception:
        pass  # Column already exists — safe to ignore


def _run_migrations(conn):
    """
    Idempotent migration steps — add any columns that may be missing
    in SQLite databases created before the multi-tenant upgrade.
    Only runs for SQLite backend.
    """
    # Multi-tenant columns
    _safe_add_column(conn, "users",     "owner_id",    "INTEGER")
    _safe_add_column(conn, "customers", "owner_id",    "INTEGER")
    _safe_add_column(conn, "inventory", "owner_id",    "INTEGER")
    _safe_add_column(conn, "orders",    "owner_id",    "INTEGER")
    _safe_add_column(conn, "workers",   "owner_id",    "INTEGER")

    # worker_code (was added in Phase 4 — keep for older DBs)
    _safe_add_column(conn, "workers",   "worker_code", "TEXT")

    # After adding owner_id columns, assign any NULL owner_ids to the first owner
    try:
        first_owner = conn.execute(
            "SELECT id FROM users WHERE role='owner' ORDER BY id LIMIT 1"
        ).fetchone()
        if first_owner:
            # _DictRow supports both row["id"] and row[0] — both work here
            oid = first_owner["id"]
            for table in ("customers", "inventory", "orders", "workers"):
                conn.execute(
                    f"UPDATE {table} SET owner_id=? WHERE owner_id IS NULL",
                    (oid,)
                )
            # For workers, also set owner_id on user accounts that are workers
            conn.execute(
                "UPDATE users SET owner_id=? WHERE role='worker' AND owner_id IS NULL",
                (oid,)
            )
        conn.commit()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT ACCOUNT SEEDING
# ─────────────────────────────────────────────────────────────────────────────
def seed_sample_data(conn):
    """
    Create the default admin owner account on first run ONLY.
    Completely idempotent — uses ON CONFLICT DO NOTHING (PostgreSQL) or
    INSERT OR IGNORE (SQLite, adapted automatically).
    No sample business data is inserted — the owner adds their own real data.
    """
    # Only run when the users table is completely empty (fresh DB)
    row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    # row[0] works on both SQLite (sqlite3.Row) and PostgreSQL (_DictRow)
    # PostgreSQL COUNT(*) column is named "count"; _DictRow maps [0] → "count"
    count = row[0] if row else 0
    if count > 0:
        return

    # Default admin owner — owner_id = NULL (they are the owner)
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password, role, full_name, owner_id) "
        "VALUES (?,?,?,?,?)",
        ("admin", hash_password("admin123"), "owner", "Admin Owner", None)
    )
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def authenticate_user(username: str, password: str):
    conn = get_connection()

    hashed = hash_password(password)
    print("Username:", username)
    print("MD5:", hashed)

    row = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    print("User row:", row)

    if row:
        print("Stored password:", row["password"])
        print("Match:", row["password"] == hashed)

    conn.close()

    if row and row["password"] == hashed:
        return dict(row)

    return None
 




def register_user(
    username: str,
    password: str,
    full_name: str,
    role: str,
    owner_id: int = None
) -> tuple:
    """
    Register a new user account.

    Args:
        username:  desired login name
        password:  plaintext (will be hashed)
        full_name: display name
        role:      'owner' or 'worker'
        owner_id:  None for owner accounts; the owner's user.id for workers

    Returns (True, user_dict) on success, (False, error_message) on failure.
    """
    conn = get_connection()

    # Check username availability
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if existing:
        conn.close()
        return False, f"Username '{username}' is already taken. Please choose another."

    try:
        hashed = hash_password(password)
        cursor = conn.execute(
            "INSERT INTO users (username, password, role, full_name, owner_id) "
            "VALUES (?,?,?,?,?)",
            (username, hashed, role, full_name, owner_id)
        )
        conn.commit()
        new_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id=?", (new_id,)).fetchone()
        conn.close()
        return True, dict(row)
    except Exception as e:
        conn.close()
        return False, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD STATS  (owner-scoped)
# ─────────────────────────────────────────────────────────────────────────────
def get_dashboard_stats(owner_id: int) -> dict:
    """Return aggregated KPI metrics for the authenticated owner's dashboard."""
    conn = get_connection()
    c = conn.cursor()

    # All fetchone()[0] calls work via _DictRow integer indexing on PostgreSQL
    # PostgreSQL COUNT(*) → column "count" → _DictRow[0] = _DictRow["count"]
    # PostgreSQL COALESCE() → column "coalesce" → _DictRow[0] = _DictRow["coalesce"]

    total_customers = c.execute(
        "SELECT COUNT(*) FROM customers WHERE owner_id=?", (owner_id,)
    ).fetchone()[0]

    total_items = c.execute(
        "SELECT COUNT(*) FROM inventory WHERE owner_id=?", (owner_id,)
    ).fetchone()[0]

    total_orders = c.execute(
        "SELECT COUNT(*) FROM orders WHERE owner_id=?", (owner_id,)
    ).fetchone()[0]

    pending_orders = c.execute(
        "SELECT COUNT(*) FROM orders WHERE owner_id=? AND status='Pending'",
        (owner_id,)
    ).fetchone()[0]

    total_revenue = c.execute(
        "SELECT COALESCE(SUM(total_amount),0) FROM orders "
        "WHERE owner_id=? AND payment_status='Paid'",
        (owner_id,)
    ).fetchone()[0]

    stock_value = c.execute(
        "SELECT COALESCE(SUM(quantity*price),0) FROM inventory WHERE owner_id=?",
        (owner_id,)
    ).fetchone()[0]

    low_stock_count = c.execute(
        "SELECT COUNT(*) FROM inventory "
        "WHERE owner_id=? AND quantity < min_stock_level",
        (owner_id,)
    ).fetchone()[0]

    pending_deliveries = c.execute(
        """SELECT COUNT(*) FROM deliveries d
           JOIN orders o ON d.order_id = o.id
           WHERE o.owner_id=? AND d.delivery_status IN ('Scheduled','Out for Delivery')""",
        (owner_id,)
    ).fetchone()[0]

    total_workers = c.execute(
        "SELECT COUNT(*) FROM workers WHERE owner_id=? AND status='Active'",
        (owner_id,)
    ).fetchone()[0]

    unpaid_balance = c.execute(
        "SELECT COALESCE(SUM(current_balance),0) FROM customers WHERE owner_id=?",
        (owner_id,)
    ).fetchone()[0]

    conn.close()
    return {
        "total_customers":    int(total_customers or 0),
        "total_items":        int(total_items or 0),
        "total_orders":       int(total_orders or 0),
        "pending_orders":     int(pending_orders or 0),
        "total_revenue":      float(total_revenue or 0),
        "stock_value":        float(stock_value or 0),
        "low_stock_count":    int(low_stock_count or 0),
        "pending_deliveries": int(pending_deliveries or 0),
        "total_workers":      int(total_workers or 0),
        "unpaid_balance":     float(unpaid_balance or 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER CRUD  (owner-scoped)
# ─────────────────────────────────────────────────────────────────────────────
def get_all_customers(owner_id: int, search: str = ""):
    """Return all customers belonging to this owner, optionally filtered."""
    conn = get_connection()
    term = f"%{search}%"
    rows = conn.execute(
        """SELECT id, business_name, contact_person, phone, address,
                  credit_limit, current_balance, created_at
           FROM customers
           WHERE owner_id=?
             AND (business_name LIKE ? OR contact_person LIKE ? OR phone LIKE ?)
           ORDER BY business_name""",
        (owner_id, term, term, term)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_customer_by_id(owner_id: int, customer_id: int):
    """Return a single customer, verifying it belongs to this owner."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM customers WHERE id=? AND owner_id=?",
        (customer_id, owner_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_customer(owner_id: int, business_name, contact_person, phone,
                 address, credit_limit, current_balance):
    """Insert a new customer for this owner."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO customers
           (owner_id, business_name, contact_person, phone, address,
            credit_limit, current_balance)
           VALUES (?,?,?,?,?,?,?)""",
        (owner_id, business_name, contact_person, phone, address,
         credit_limit, current_balance)
    )
    conn.commit()
    conn.close()


def update_customer(owner_id: int, customer_id, business_name, contact_person,
                    phone, address, credit_limit, current_balance):
    """Update a customer record, scoped to owner_id for safety."""
    conn = get_connection()
    conn.execute(
        """UPDATE customers
           SET business_name=?, contact_person=?, phone=?, address=?,
               credit_limit=?, current_balance=?
           WHERE id=? AND owner_id=?""",
        (business_name, contact_person, phone, address,
         credit_limit, current_balance, customer_id, owner_id)
    )
    conn.commit()
    conn.close()


def delete_customer(owner_id: int, customer_id: int):
    """Delete a customer, verifying ownership."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM customers WHERE id=? AND owner_id=?",
        (customer_id, owner_id)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# INVENTORY CRUD  (owner-scoped)
# ─────────────────────────────────────────────────────────────────────────────
def get_all_inventory(owner_id: int, search: str = "", category: str = "All"):
    """Return all inventory items for this owner, optionally filtered."""
    conn = get_connection()
    term = f"%{search}%"
    rows = conn.execute(
        """SELECT id, sku, name, category, quantity, unit, price, cost,
                  min_stock_level,
                  CASE WHEN quantity < min_stock_level THEN 1 ELSE 0 END AS low_stock
           FROM inventory
           WHERE owner_id=?
             AND (name LIKE ? OR sku LIKE ? OR category LIKE ?)
             AND (? = 'All' OR category = ?)
           ORDER BY category, name""",
        (owner_id, term, term, term, category, category)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_inventory_categories(owner_id: int):
    """Return distinct categories for this owner's inventory."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT category FROM inventory WHERE owner_id=? ORDER BY category",
        (owner_id,)
    ).fetchall()
    conn.close()
    # row["category"] works via _DictRow string key — no integer indexing needed
    return ["All"] + [r["category"] for r in rows if r["category"]]


def get_item_by_id(owner_id: int, item_id: int):
    """Return a single inventory item, verifying ownership."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM inventory WHERE id=? AND owner_id=?",
        (item_id, owner_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_inventory_item(owner_id: int, sku, name, category, quantity,
                       unit, price, cost, min_stock_level):
    """Insert a new inventory item. Returns (True, msg) or (False, error)."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO inventory
               (owner_id, sku, name, category, quantity, unit, price, cost, min_stock_level)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (owner_id, sku, name, category, quantity, unit, price, cost, min_stock_level)
        )
        conn.commit()
        return True, "Item added successfully."
    except Exception as e:
        err = str(e).lower()
        if "unique" in err or "duplicate" in err:
            return False, f"SKU '{sku}' already exists in your inventory."
        return False, str(e)
    finally:
        conn.close()


def update_inventory_item(owner_id: int, item_id, sku, name, category, quantity,
                           unit, price, cost, min_stock_level):
    """Update an inventory item. Returns (True, msg) or (False, error)."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE inventory
               SET sku=?, name=?, category=?, quantity=?, unit=?,
                   price=?, cost=?, min_stock_level=?
               WHERE id=? AND owner_id=?""",
            (sku, name, category, quantity, unit, price, cost, min_stock_level,
             item_id, owner_id)
        )
        conn.commit()
        return True, "Item updated successfully."
    except Exception as e:
        err = str(e).lower()
        if "unique" in err or "duplicate" in err:
            return False, f"SKU '{sku}' already exists for another item."
        return False, str(e)
    finally:
        conn.close()


def delete_inventory_item(owner_id: int, item_id: int):
    """Delete an inventory item, verifying ownership."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM inventory WHERE id=? AND owner_id=?",
        (item_id, owner_id)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# ORDER WORKFLOW HELPERS  (owner-scoped)
# ─────────────────────────────────────────────────────────────────────────────
def get_all_orders(owner_id: int):
    """Return all orders for this owner with customer name included."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT o.id, c.business_name AS customer, o.order_date,
                  o.status, o.total_amount, o.payment_status
           FROM orders o
           JOIN customers c ON o.customer_id = c.id
           WHERE o.owner_id=?
           ORDER BY o.order_date DESC""",
        (owner_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_customers_for_dropdown(owner_id: int):
    """Return customers for the order-creation dropdown."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, business_name, contact_person, phone, address,
                  credit_limit, current_balance
           FROM customers WHERE owner_id=? ORDER BY business_name""",
        (owner_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_inventory_in_stock(owner_id: int):
    """Return items with quantity > 0 for the add-item dropdown."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, sku, name, category, quantity, unit, price
           FROM inventory WHERE owner_id=? AND quantity > 0
           ORDER BY category, name""",
        (owner_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_current_stock(owner_id: int, item_id: int) -> int:
    """Return live quantity for a single item (stock validation before add-to-cart)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT quantity FROM inventory WHERE id=? AND owner_id=?",
        (item_id, owner_id)
    ).fetchone()
    conn.close()
    # row["quantity"] via _DictRow — also row[0] works identically
    return int(row["quantity"]) if row else 0


def create_full_order(owner_id: int, customer_id: int,
                      cart: list, amount_received: float):
    """
    Atomic transaction: create order + items, deduct stock, update customer balance.

    cart items: dicts with keys item_id, name, quantity, price, unit
    Returns (True, order_id) on success or (False, error_message) on failure.
    """
    conn = get_connection()
    try:
        # Calculate totals
        total_amount = sum(item["quantity"] * item["price"] for item in cart)
        amount_received = min(amount_received, total_amount)
        outstanding = total_amount - amount_received

        if amount_received >= total_amount:
            payment_status = "Paid"
        elif amount_received > 0:
            payment_status = "Partial"
        else:
            payment_status = "Unpaid"

        # Pre-flight stock validation (owner-scoped)
        for item in cart:
            row = conn.execute(
                "SELECT quantity FROM inventory WHERE id=? AND owner_id=?",
                (item["item_id"], owner_id)
            ).fetchone()
            available = int(row["quantity"]) if row else 0
            if available < item["quantity"]:
                return False, (
                    f"Insufficient stock for '{item['name']}'. "
                    f"Available: {available} {item['unit']}, "
                    f"Requested: {item['quantity']}"
                )

        # Insert order (with owner_id)
        cursor = conn.execute(
            """INSERT INTO orders (owner_id, customer_id, status, total_amount, payment_status)
               VALUES (?, ?, 'Processing', ?, ?)""",
            (owner_id, customer_id, total_amount, payment_status)
        )
        order_id = cursor.lastrowid

        # Insert order items + deduct stock
        for item in cart:
            conn.execute(
                """INSERT INTO order_items (order_id, item_id, quantity, price_at_order)
                   VALUES (?,?,?,?)""",
                (order_id, item["item_id"], item["quantity"], item["price"])
            )
            conn.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE id=? AND owner_id=?",
                (item["quantity"], item["item_id"], owner_id)
            )

        # Update customer outstanding balance
        conn.execute(
            "UPDATE customers SET current_balance = current_balance + ? "
            "WHERE id=? AND owner_id=?",
            (outstanding, customer_id, owner_id)
        )

        # Auto-create a Scheduled delivery record
        conn.execute(
            "INSERT INTO deliveries (order_id, delivery_status) VALUES (?, 'Scheduled')",
            (order_id,)
        )

        conn.commit()
        return True, order_id

    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def get_order_items_detail(owner_id: int, order_id: int):
    """Return line items with inventory details for a specific order."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT oi.quantity, oi.price_at_order, i.name, i.unit, i.sku,
                  (oi.quantity * oi.price_at_order) AS line_total
           FROM order_items oi
           JOIN inventory i ON oi.item_id = i.id
           JOIN orders o    ON oi.order_id = o.id
           WHERE oi.order_id=? AND o.owner_id=?""",
        (order_id, owner_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# DELIVERY MANAGEMENT  (owner-scoped)
# ─────────────────────────────────────────────────────────────────────────────
def get_all_deliveries_detailed(owner_id: int):
    """Return all deliveries with order, customer, and worker context for this owner."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT d.id, d.order_id, d.delivery_status, d.delivery_date, d.notes,
                  d.worker_id,
                  o.total_amount, o.payment_status, o.status AS order_status,
                  o.customer_id,
                  c.business_name, c.phone, c.address,
                  w.name AS worker_name
           FROM deliveries d
           JOIN orders o    ON d.order_id  = o.id
           JOIN customers c ON o.customer_id = c.id
           LEFT JOIN workers w ON d.worker_id = w.id
           WHERE o.owner_id=?
           ORDER BY d.id DESC""",
        (owner_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_assignable_workers(owner_id: int):
    """Return active workers available to be assigned deliveries for this owner."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, role FROM workers WHERE owner_id=? AND status='Active' ORDER BY name",
        (owner_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def assign_delivery_to_worker(owner_id: int, delivery_id: int, worker_id: int):
    """Assign a delivery to a worker and set status → 'Out for Delivery'."""
    conn = get_connection()
    conn.execute(
        """UPDATE deliveries
           SET worker_id=?, delivery_status='Out for Delivery',
               delivery_date=CURRENT_TIMESTAMP
           WHERE id=?
             AND order_id IN (SELECT id FROM orders WHERE owner_id=?)""",
        (worker_id, delivery_id, owner_id)
    )
    conn.execute(
        """UPDATE orders SET status='Processing'
           WHERE id=(SELECT order_id FROM deliveries WHERE id=?)
             AND owner_id=?""",
        (delivery_id, owner_id)
    )
    conn.commit()
    conn.close()


def update_delivery_status_only(owner_id: int, delivery_id: int,
                                new_status: str, notes: str = ""):
    """Update delivery status (used by owner)."""
    conn = get_connection()
    if new_status == "Delivered":
        conn.execute(
            """UPDATE deliveries
               SET delivery_status=?, delivery_date=CURRENT_TIMESTAMP, notes=?
               WHERE id=?
                 AND order_id IN (SELECT id FROM orders WHERE owner_id=?)""",
            (new_status, notes or "Marked delivered by owner", delivery_id, owner_id)
        )
        conn.execute(
            """UPDATE orders SET status='Delivered'
               WHERE id=(SELECT order_id FROM deliveries WHERE id=?)
                 AND owner_id=?""",
            (delivery_id, owner_id)
        )
    elif new_status == "Scheduled":
        conn.execute(
            """UPDATE deliveries
               SET delivery_status='Scheduled', worker_id=NULL
               WHERE id=?
                 AND order_id IN (SELECT id FROM orders WHERE owner_id=?)""",
            (delivery_id, owner_id)
        )
    else:
        conn.execute(
            """UPDATE deliveries SET delivery_status=?, notes=?
               WHERE id=?
                 AND order_id IN (SELECT id FROM orders WHERE owner_id=?)""",
            (new_status, notes, delivery_id, owner_id)
        )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# WORKER DELIVERY DASHBOARD  (worker-scoped — already safe by worker_id)
# ─────────────────────────────────────────────────────────────────────────────
def get_worker_id_for_user(user_id: int):
    """
    Return the workers.id linked to this user account.
    Tries direct user_id link first; falls back to name match (lazy migration).
    All row access uses string keys for clarity and robustness.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM workers WHERE user_id=?", (user_id,)
    ).fetchone()
    if not row:
        user = conn.execute(
            "SELECT full_name, owner_id FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if user and user["full_name"]:
            # Match by name, scoped to the owner this worker belongs to
            owner_ctx = user["owner_id"]  # the worker's owner_id
            if owner_ctx:
                row = conn.execute(
                    "SELECT id FROM workers WHERE name=? AND owner_id=?",
                    (user["full_name"], owner_ctx)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT id FROM workers WHERE name=?", (user["full_name"],)
                ).fetchone()
            if row:
                # Persist the link
                conn.execute(
                    "UPDATE workers SET user_id=? WHERE id=?",
                    (user_id, row["id"])
                )
                conn.commit()
    conn.close()
    return row["id"] if row else None


def get_deliveries_for_worker(worker_id: int):
    """Return active deliveries assigned to this worker with customer details."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT d.id, d.order_id, d.delivery_status, d.delivery_date, d.notes,
                  o.total_amount, o.payment_status, o.customer_id,
                  c.business_name, c.phone, c.address, c.contact_person
           FROM deliveries d
           JOIN orders o    ON d.order_id   = o.id
           JOIN customers c ON o.customer_id = c.id
           WHERE d.worker_id = ?
             AND d.delivery_status NOT IN ('Delivered', 'Failed')
           ORDER BY d.id DESC""",
        (worker_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_completed_deliveries_for_worker(worker_id: int):
    """Return completed deliveries for a worker's history section."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT d.id, d.order_id, d.delivery_status, d.delivery_date, d.notes,
                  o.total_amount, o.payment_status,
                  c.business_name
           FROM deliveries d
           JOIN orders o    ON d.order_id   = o.id
           JOIN customers c ON o.customer_id = c.id
           WHERE d.worker_id = ?
             AND d.delivery_status IN ('Delivered', 'Failed')
           ORDER BY d.delivery_date DESC
           LIMIT 20""",
        (worker_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_delivery_outcome(
    delivery_id: int,
    order_id: int,
    customer_id: int,
    worker_id: int,
    outcome: str,
    amount_collected: float = 0.0,
    payment_mode: str = "Cash",
    fail_reason: str = ""
) -> tuple:
    """
    Complete delivery outcome — atomically:
      1. Updates delivery status & timestamp
      2. Updates order status & payment_status
      3. Adjusts customer.current_balance
      4. Inserts row into payment_history

    outcome values: 'full' | 'partial' | 'none' | 'failed'
    Uses explicit string key access on all rows for PostgreSQL compatibility.
    """
    conn = get_connection()
    try:
        order = conn.execute(
            "SELECT total_amount, payment_status FROM orders WHERE id=?",
            (order_id,)
        ).fetchone()
        total      = float(order["total_amount"])
        old_pay_st = order["payment_status"]

        cust = conn.execute(
            "SELECT current_balance FROM customers WHERE id=?",
            (customer_id,)
        ).fetchone()
        current_bal = float(cust["current_balance"])

        if outcome == "failed":
            notes = fail_reason or "Delivery failed"
            conn.execute(
                "UPDATE deliveries SET delivery_status='Failed', "
                "delivery_date=CURRENT_TIMESTAMP, notes=? WHERE id=?",
                (notes, delivery_id)
            )
            conn.execute(
                """INSERT INTO payment_history
                   (order_id, delivery_id, worker_id, amount, payment_mode, outcome, notes)
                   VALUES (?,?,?,0,'—','failed',?)""",
                (order_id, delivery_id, worker_id, notes)
            )
        else:
            if outcome == "full":
                new_bal    = max(0.0, current_bal - total)
                new_pay_st = "Paid"
                collected  = total
            elif outcome == "partial":
                collected  = float(amount_collected)
                new_bal    = max(0.0, current_bal - collected)
                new_pay_st = "Partial" if collected < total else "Paid"
            else:  # 'none'
                collected  = 0.0
                new_bal    = current_bal
                new_pay_st = old_pay_st

            notes = (
                f"{payment_mode} collected: ₹{collected:,.0f}"
                if collected > 0 else "No payment collected"
            )

            conn.execute(
                "UPDATE customers SET current_balance=? WHERE id=?",
                (new_bal, customer_id)
            )
            conn.execute(
                "UPDATE orders SET payment_status=?, status='Delivered' WHERE id=?",
                (new_pay_st, order_id)
            )
            conn.execute(
                """UPDATE deliveries
                   SET delivery_status='Delivered',
                       delivery_date=CURRENT_TIMESTAMP,
                       notes=?
                   WHERE id=?""",
                (notes, delivery_id)
            )
            conn.execute(
                """INSERT INTO payment_history
                   (order_id, delivery_id, worker_id, amount, payment_mode, outcome, notes)
                   VALUES (?,?,?,?,?,?,?)""",
                (order_id, delivery_id, worker_id, collected,
                 payment_mode, outcome, notes)
            )

        conn.commit()
        return True, "Delivery outcome recorded successfully."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


# Backward-compatible alias
def record_cash_collection(
    delivery_id: int, order_id: int, customer_id: int, amount_collected: float
):
    """Legacy wrapper — use record_delivery_outcome() for new code."""
    outcome = "full" if amount_collected > 0 else "none"
    return record_delivery_outcome(
        delivery_id=delivery_id, order_id=order_id, customer_id=customer_id,
        worker_id=0, outcome=outcome, amount_collected=amount_collected
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT DASHBOARD METRICS  (owner-scoped)
# ─────────────────────────────────────────────────────────────────────────────
def get_today_collections(owner_id: int, query_date: str = None) -> dict:
    """
    Return today's payment collection summary for this owner's workers.
    query_date: 'YYYY-MM-DD' string; defaults to today.
    DATE(col) is converted to (col)::date by _adapt_sql() for PostgreSQL.
    """
    if not query_date:
        query_date = str(date.today())

    conn = get_connection()
    try:
        # Total collected today (scoped to this owner's orders)
        # DATE(ph.collected_at) → (ph.collected_at)::date via _adapt_sql
        total_row = conn.execute(
            """SELECT COALESCE(SUM(ph.amount), 0)
               FROM payment_history ph
               JOIN orders o ON ph.order_id = o.id
               WHERE o.owner_id=? AND DATE(ph.collected_at) = ?""",
            (owner_id, query_date)
        ).fetchone()
        total = float(total_row[0]) if total_row else 0.0

        # Worker-wise breakdown (scoped to owner's workers)
        worker_rows = conn.execute(
            """SELECT w.name AS worker_name,
                      COUNT(ph.id)    AS deliveries,
                      COALESCE(SUM(ph.amount), 0) AS collected
               FROM payment_history ph
               LEFT JOIN workers w ON ph.worker_id = w.id
               JOIN orders o ON ph.order_id = o.id
               WHERE o.owner_id=? AND DATE(ph.collected_at) = ?
               GROUP BY ph.worker_id, w.name
               ORDER BY collected DESC""",
            (owner_id, query_date)
        ).fetchall()
        workers = [dict(r) for r in worker_rows]

        # Delivered count today (scoped to owner)
        del_row = conn.execute(
            """SELECT COUNT(*) FROM deliveries d
               JOIN orders o ON d.order_id = o.id
               WHERE o.owner_id=?
                 AND d.delivery_status='Delivered'
                 AND DATE(d.delivery_date)=?""",
            (owner_id, query_date)
        ).fetchone()
        delivered = int(del_row[0]) if del_row else 0

        # Failed count today
        fail_row = conn.execute(
            """SELECT COUNT(*) FROM deliveries d
               JOIN orders o ON d.order_id = o.id
               WHERE o.owner_id=?
                 AND d.delivery_status='Failed'
                 AND DATE(d.delivery_date)=?""",
            (owner_id, query_date)
        ).fetchone()
        failed = int(fail_row[0]) if fail_row else 0

        return {
            "date":      query_date,
            "total":     total,
            "workers":   workers,
            "delivered": delivered,
            "failed":    failed,
        }
    finally:
        conn.close()


def get_outstanding_balances(owner_id: int) -> list:
    """Return customers with outstanding balance > 0 for this owner."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, business_name, phone, current_balance
           FROM customers
           WHERE owner_id=? AND current_balance > 0
           ORDER BY current_balance DESC""",
        (owner_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_payment_history_for_order(owner_id: int, order_id: int) -> list:
    """Return all payment events for a given order (ownership verified)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT ph.*, w.name AS worker_name
           FROM payment_history ph
           LEFT JOIN workers w ON ph.worker_id = w.id
           JOIN orders o ON ph.order_id = o.id
           WHERE ph.order_id=? AND o.owner_id=?
           ORDER BY ph.collected_at DESC""",
        (order_id, owner_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_worker_total_today(worker_id: int) -> float:
    """Return total amount collected by a specific worker today."""
    today = str(date.today())
    conn  = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payment_history "
        "WHERE worker_id=? AND DATE(collected_at)=?",
        (worker_id, today)
    ).fetchone()
    conn.close()
    # row[0] works via _DictRow: first column is the COALESCE result
    return float(row[0]) if row else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# WORKER MANAGEMENT CRUD  (owner-scoped)
# ─────────────────────────────────────────────────────────────────────────────
def generate_worker_code(conn, owner_id: int) -> str:
    """
    Generate a unique worker invite code (format: WK-XXXXXX).
    Uniqueness is checked globally across all workers.
    """
    chars = string.ascii_uppercase + string.digits
    while True:
        suffix = "".join(random.choices(chars, k=6))
        code = f"WK-{suffix}"
        exists = conn.execute(
            "SELECT id FROM workers WHERE worker_code=?", (code,)
        ).fetchone()
        if not exists:
            return code


def add_worker(owner_id: int, name: str, role: str, phone: str) -> tuple:
    """
    Create a new worker record under this owner.
    Returns (worker_id, worker_code).
    """
    conn = get_connection()
    code = generate_worker_code(conn, owner_id)
    cursor = conn.execute(
        """INSERT INTO workers (owner_id, name, role, phone, status, worker_code)
           VALUES (?, ?, ?, ?, 'Active', ?)""",
        (owner_id, name, role, phone or "", code)
    )
    conn.commit()
    wid = cursor.lastrowid
    conn.close()
    return wid, code


def update_worker(owner_id: int, worker_id: int, name: str,
                  role: str, phone: str, status: str):
    """Update a worker's details (does NOT change worker_code)."""
    conn = get_connection()
    conn.execute(
        "UPDATE workers SET name=?, role=?, phone=?, status=? "
        "WHERE id=? AND owner_id=?",
        (name, role, phone, status, worker_id, owner_id)
    )
    conn.commit()
    conn.close()


def delete_worker(owner_id: int, worker_id: int):
    """Delete a worker record (user account kept). Ownership verified."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM workers WHERE id=? AND owner_id=?",
        (worker_id, owner_id)
    )
    conn.commit()
    conn.close()


def get_all_workers(owner_id: int):
    """Return all workers for this owner."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, role, status, phone FROM workers "
        "WHERE owner_id=? ORDER BY name",
        (owner_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_worker_by_code(code: str):
    """
    Return the worker record matching this invite code, or None.
    Also returns None if the code has already been used (user_id is set).
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM workers WHERE worker_code=?",
        (code.strip().upper(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def link_user_to_worker(user_id: int, worker_id: int):
    """Bind a newly registered user account to their worker record."""
    conn = get_connection()
    conn.execute(
        "UPDATE workers SET user_id=? WHERE id=?",
        (user_id, worker_id)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# INITIALISE DATABASE  (called once at app startup)
# ─────────────────────────────────────────────────────────────────────────────
def init_db():
    """
    Create all tables, run safe column migrations, seed default account.
    Completely idempotent — safe to call on every Streamlit run.

    PostgreSQL (Supabase):
      - create_tables() and _run_migrations() are SKIPPED — the schema is
        managed via supabase_schema.sql in the Supabase SQL Editor.
      - seed_sample_data() runs but is idempotent (ON CONFLICT DO NOTHING).

    SQLite (local development):
      - All three steps run in sequence.
    """
    conn = get_connection()

    if not is_postgres():
        # SQLite only — create schema and run migrations
        create_tables(conn)
        _run_migrations(conn)

    # Seed default admin account — safe on both backends
    seed_sample_data(conn)

    conn.close()
    return backend_name()
