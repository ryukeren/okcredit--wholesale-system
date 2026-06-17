"""
database.py — Database Abstraction Layer
==========================================
Provides a unified get_connection() that returns either:
  - Supabase PostgreSQL  (when .streamlit/secrets.toml has [supabase] db_url)
  - Local SQLite         (fallback — wholesale.db next to this file)

The PostgreSQL wrapper is API-compatible with sqlite3 so ALL existing
db.py code works unchanged. Conversions handled automatically:
  ?                                   →  %s
  INTEGER PRIMARY KEY AUTOINCREMENT   →  SERIAL PRIMARY KEY
  INSERT OR IGNORE                    →  INSERT ... ON CONFLICT DO NOTHING
  PRAGMA ...                          →  ignored (no-op)
  .lastrowid                          →  captured via RETURNING id
  DATE(col)                           →  (col)::date
  row[0] / row[1]                     →  _DictRow integer indexing

Critical Fix — _DictRow:
  psycopg2 RealDictCursor returns RealDictRow objects which only support
  string key access (row["col"]).  sqlite3.Row supports BOTH string keys
  AND integer indices (row[0]).  _DictRow wraps RealDictRow to support
  both, making every row[0] / row[1] / fetchone()[0] call work identically
  to the SQLite version — no changes needed anywhere else in the codebase.

Usage (identical to sqlite3):
    conn = get_connection()
    row  = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    val  = row[0]          # integer index — works on PostgreSQL too
    val  = row["username"] # string key   — works on both backends
    conn.commit()
    conn.close()
"""

import re
import os
import sqlite3

# ── Local SQLite path ─────────────────────────────────────────────────────────
_DB_PATH = os.path.join(os.path.dirname(__file__), "wholesale.db")

# ── Compiled SQL transformation patterns ─────────────────────────────────────
_RE_PLACEHOLDER      = re.compile(r'\?')
_RE_AUTOINCREMENT    = re.compile(r'\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b', re.IGNORECASE)
_RE_INSERT_OR_IGNORE = re.compile(r'\bINSERT\s+OR\s+IGNORE\b', re.IGNORECASE)
_RE_IS_INSERT        = re.compile(r'^\s*INSERT\b', re.IGNORECASE)
_RE_PRAGMA           = re.compile(r'^\s*PRAGMA\b', re.IGNORECASE)
_RE_RETURNING        = re.compile(r'\bRETURNING\b', re.IGNORECASE)
# DATE(col) → (col)::date  — PostgreSQL does not guarantee DATE() as a function
_RE_DATE_FUNC        = re.compile(r'\bDATE\(([^)]+)\)', re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def _get_supabase_url() -> str:
    """Return Supabase PostgreSQL URL from secrets or environment, or empty string."""
    # Try Streamlit secrets first
    try:
        import streamlit as st
        url = st.secrets.get("supabase", {}).get("db_url", "")
        if url:
            return str(url)
    except Exception:
        pass
    # Fallback to environment variable
    return os.environ.get("SUPABASE_DB_URL", "")


def is_postgres() -> bool:
    """Return True when the app is configured to use Supabase PostgreSQL."""
    return bool(_get_supabase_url())


def backend_name() -> str:
    """Return 'postgresql' or 'sqlite' — useful for debug / admin info."""
    return "postgresql" if is_postgres() else "sqlite"


# ─────────────────────────────────────────────────────────────────────────────
# ROW WRAPPER  — makes PostgreSQL rows behave like sqlite3.Row
# ─────────────────────────────────────────────────────────────────────────────

class _DictRow:
    """
    Wraps a psycopg2 RealDictRow so that BOTH dict-style (row["col"])
    AND integer-index-style (row[0], row[1]) access work — exactly like
    sqlite3.Row.

    This single class eliminates every KeyError: 0 / KeyError: 1 caused
    by PostgreSQL's RealDictCursor returning dict-only rows instead of
    the tuple-indexable rows that sqlite3 produces.

    dict(row) also works correctly because _DictRow implements the full
    mapping protocol (keys() + __getitem__).
    """

    __slots__ = ("_data", "_keys")

    def __init__(self, mapping):
        import decimal
        # Materialise into a plain dict so column order is preserved
        # Cast decimal.Decimal to float to maintain compatibility with SQLite (which returned float)
        self._data = {}
        for k, v in mapping.items():
            if isinstance(v, decimal.Decimal):
                self._data[k] = float(v)
            else:
                self._data[k] = v
        self._keys = list(self._data.keys())

    # ── Index access: row[0], row["col"] ─────────────────────────────────────
    def __getitem__(self, key):
        if isinstance(key, int):
            try:
                return self._data[self._keys[key]]
            except IndexError:
                raise IndexError(
                    f"_DictRow index {key} out of range "
                    f"(row has {len(self._keys)} columns: {self._keys})"
                )
        return self._data[key]

    # ── Mapping helpers (needed so dict(row) works) ───────────────────────────
    def get(self, key, default=None):
        if isinstance(key, int):
            try:
                return self._data[self._keys[key]]
            except IndexError:
                return default
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __iter__(self):
        """Iterating yields column names (like sqlite3.Row and dict)."""
        return iter(self._data)

    def __contains__(self, key):
        return key in self._data

    def __bool__(self):
        return bool(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"_DictRow({self._data!r})"


# ─────────────────────────────────────────────────────────────────────────────
# SQL ADAPTATION HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _adapt_sql(sql: str):
    """
    Convert SQLite-dialect SQL to PostgreSQL.
    Returns (adapted_sql, is_insert) or (None, False) for PRAGMA (skip).
    """
    if _RE_PRAGMA.match(sql):
        return None, False  # PRAGMA → no-op in PostgreSQL

    # ? → %s
    sql = _RE_PLACEHOLDER.sub('%s', sql)

    # INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
    sql = _RE_AUTOINCREMENT.sub('SERIAL PRIMARY KEY', sql)

    # DATE(col) → (col)::date  (SQLite DATE() → PostgreSQL cast)
    sql = _RE_DATE_FUNC.sub(r'(\1)::date', sql)

    # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
    had_or_ignore = bool(_RE_INSERT_OR_IGNORE.search(sql))
    sql = _RE_INSERT_OR_IGNORE.sub('INSERT', sql)

    # Append RETURNING id to INSERT statements (enables lastrowid)
    is_insert = (
        bool(_RE_IS_INSERT.match(sql)) and
        not _RE_RETURNING.search(sql)
    )
    if is_insert:
        sql = sql.rstrip('; \n\r\t')
        if had_or_ignore:
            sql += ' ON CONFLICT DO NOTHING'
        sql += ' RETURNING id'

    return sql, is_insert


# ─────────────────────────────────────────────────────────────────────────────
# POSTGRESQL CURSOR WRAPPER
# ─────────────────────────────────────────────────────────────────────────────

class _PGCursor:
    """
    Wraps psycopg2 cursor to expose sqlite3-compatible interface.
    All rows are returned as _DictRow objects so both dict-style
    and integer-index access work transparently.
    """

    def __init__(self, raw_cursor, last_id=None):
        self._cur     = raw_cursor
        self._last_id = last_id

    def fetchall(self):
        if self._cur is None:
            return []
        try:
            rows = self._cur.fetchall()
            # Wrap every row in _DictRow for integer-index compatibility
            return [_DictRow(r) for r in rows] if rows else []
        except Exception:
            return []

    def fetchone(self):
        if self._cur is None:
            return None
        try:
            row = self._cur.fetchone()
            # Wrap in _DictRow so row[0] and row["col"] both work
            return _DictRow(row) if row is not None else None
        except Exception:
            return None

    @property
    def lastrowid(self):
        return self._last_id

    def __iter__(self):
        return iter(self.fetchall())

    def __getitem__(self, key):
        """Allow cursor["col"] as a shortcut for cursor.fetchone()["col"]."""
        row = self.fetchone()
        return row[key] if row else None


# ─────────────────────────────────────────────────────────────────────────────
# POSTGRESQL CONNECTION WRAPPER
# ─────────────────────────────────────────────────────────────────────────────

class _PGConn:
    """
    Wraps psycopg2.connect() with a sqlite3-compatible API.
    All SQL is adapted transparently via _adapt_sql().
    Rows are returned as _DictRow objects (supports both dict and int access).
    """

    def __init__(self, dsn: str):
        try:
            import psycopg2
            import psycopg2.extras
            self._conn = psycopg2.connect(
                dsn,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            self._conn.autocommit = False
        except ImportError:
            raise ImportError(
                "psycopg2-binary is required for Supabase support.\n"
                "Run: pip install psycopg2-binary"
            )

    def execute(self, sql: str, params=None):
        adapted, is_insert = _adapt_sql(sql)

        if adapted is None:           # PRAGMA — return empty no-op cursor
            return _PGCursor(None)

        cur = self._conn.cursor()
        try:
            cur.execute(adapted, tuple(params) if params else None)
        except Exception:
            self._conn.rollback()
            raise

        last_id = None
        if is_insert:
            try:
                row = cur.fetchone()
                if row:
                    # RETURNING id gives us the new row id
                    # row is a RealDictRow here (before _DictRow wrapping)
                    val = row.get('id') if hasattr(row, 'get') else row[0]
                    last_id = val
            except Exception:
                pass

        return _PGCursor(cur, last_id)

    def executemany(self, sql: str, data):
        adapted, _ = _adapt_sql(sql)

        if adapted is None:
            return _PGCursor(None)

        # Remove RETURNING id — not valid in executemany
        adapted = re.sub(
            r'\s+RETURNING\s+id\s*$', '', adapted, flags=re.IGNORECASE
        )

        cur = self._conn.cursor()
        try:
            cur.executemany(adapted, [tuple(row) for row in data])
        except Exception:
            self._conn.rollback()
            raise
        return _PGCursor(cur)

    def cursor(self):
        """Return self so that conn.cursor().execute() works like conn.execute()."""
        return self

    def commit(self):
        self._conn.commit()

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# SQLITE WRAPPER  (thin pass-through)
# ─────────────────────────────────────────────────────────────────────────────

class _SQLiteConn:
    """
    Thin wrapper around sqlite3.Connection for interface consistency.
    Enables foreign keys and sets row_factory automatically.
    sqlite3.Row already supports both row["col"] and row[0] natively.
    """

    def __init__(self, db_path: str):
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        self._conn = conn

    def execute(self, sql: str, params=None):
        if params:
            return self._conn.execute(sql, params)
        return self._conn.execute(sql)

    def executemany(self, sql: str, data):
        return self._conn.executemany(sql, data)

    def cursor(self):
        """Return self so that conn.cursor().execute() works like conn.execute()."""
        return self

    def commit(self):
        self._conn.commit()

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def close(self):
        self._conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def get_connection():
    """
    Return a database connection auto-selected from available config:

    1. Supabase PostgreSQL — when .streamlit/secrets.toml contains:
           [supabase]
           db_url = "postgresql://postgres.xxxx:password@...supabase.com:6543/postgres"

    2. Local SQLite (wholesale.db) — automatic fallback when no Supabase config.

    Both return objects with identical interface:
        conn.execute(sql, params?)  → cursor with .fetchall(), .fetchone(), .lastrowid
        conn.executemany(sql, data)
        conn.commit() / .rollback() / .close()

    Row objects support BOTH:
        row["column_name"]  — dict-style (PostgreSQL native)
        row[0], row[1]      — integer index (SQLite compatibility)
    """
    url = _get_supabase_url()
    if url:
        return _PGConn(url)
    return _SQLiteConn(_DB_PATH)
