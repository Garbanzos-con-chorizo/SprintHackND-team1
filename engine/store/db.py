"""Where the store lives and how to open it (V2.1). The schema is schema.sql next to this file."""
import os
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")
DEFAULT_PATH = Path("out") / "store" / "ecom.db"


def db_path(path: str | Path | None = None) -> Path:
    """An explicit path wins, then the ECOM_DB setting, then out/store/ecom.db."""
    return Path(path or os.environ.get("ECOM_DB") or DEFAULT_PATH)


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open the store and make sure every table and view exists (init is safe to repeat)."""
    p = db_path(path)
    if str(p) != ":memory:":
        p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    init(conn)
    return conn


# Columns added after version 1: CREATE TABLE IF NOT EXISTS leaves an existing table as it was,
# so init adds them in place. Adding a column never breaks a reader.
ADDED_COLUMNS = {
    "transactions": [("shipping_cents", "INTEGER NOT NULL DEFAULT 0"), ("handling_cents", "INTEGER NOT NULL DEFAULT 0")],
}


def init(conn: sqlite3.Connection) -> int:
    """Create the tables and views from schema.sql, add columns newer than the database; returns the
    schema version."""
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    for table, columns in ADDED_COLUMNS.items():
        have = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, decl in columns:
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
    conn.commit()
    return conn.execute("PRAGMA user_version").fetchone()[0]
