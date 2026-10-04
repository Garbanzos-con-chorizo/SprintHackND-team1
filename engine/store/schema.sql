-- Store schema, version 1. Contract: docs/contracts/store.md. Owner: Victor (engine/store/).
-- Plain SQL on purpose, so it ports to Azure SQL or Postgres. SQLite-only bits are marked "sqlite:".
-- Safe to run on an existing database: every statement is IF NOT EXISTS.
--
-- Conventions: money is INTEGER cents; dates are TEXT 'YYYY-MM-DD' (Eastern business date);
-- timestamps are TEXT ISO 8601 with offset; key columns are never NULL ('' = "no dimension");
-- a NULL measure means "no data", never 0.

PRAGMA user_version = 1;  -- sqlite: schema version

-- One row per sale or refund: the columns of docs/contracts/transaction.md, plus load bookkeeping.
CREATE TABLE IF NOT EXISTS transactions (
    txn_id          TEXT    NOT NULL PRIMARY KEY,
    source          TEXT    NOT NULL,
    marketplace     TEXT    NOT NULL,
    type            TEXT    NOT NULL,              -- sale | refund (phase 3 adds payout)
    business_date   TEXT    NOT NULL,
    order_id        TEXT    NOT NULL,
    customer_id     TEXT    NOT NULL DEFAULT '',   -- '' when the source has no buyer id
    customer_basis  TEXT    NOT NULL,              -- buyer | order
    gross_cents     INTEGER NOT NULL,
    fee_cents       INTEGER NOT NULL DEFAULT 0,
    units           INTEGER,                       -- NULL until the engine reports units (V2.7)
    source_file     TEXT    NOT NULL,
    source_row      INTEGER NOT NULL,
    run_id          TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions (business_date, marketplace);
CREATE INDEX IF NOT EXISTS ix_transactions_customer ON transactions (marketplace, customer_id);

-- One row per business date and marketplace, copied from out/pulse/<date>.json (docs/contracts/pulse.md).
-- When status is not 'ok' every measure is NULL, as in the pulse.
CREATE TABLE IF NOT EXISTS pulse_daily (
    business_date   TEXT    NOT NULL,
    marketplace     TEXT    NOT NULL,              -- shopgoodwill | amazon | ebay | other
    status          TEXT    NOT NULL,              -- ok | missing | stale | unknown | not_configured
    gross_cents     INTEGER,
    refunds_cents   INTEGER,
    revenue_cents   INTEGER,
    fees_cents      INTEGER,
    orders          INTEGER,
    customers       INTEGER,
    customer_basis  TEXT,                          -- buyer | order | mixed
    run_id          TEXT    NOT NULL,
    PRIMARY KEY (business_date, marketplace)
);

-- Internal API snapshot: one row per business date, metric and dimension.
-- Metric names, units and dimensions: docs/contracts/internal-api.md.
CREATE TABLE IF NOT EXISTS internal_daily (
    business_date   TEXT    NOT NULL,
    metric          TEXT    NOT NULL,
    dimension       TEXT    NOT NULL DEFAULT '',
    value           REAL    NOT NULL,
    unit            TEXT    NOT NULL,
    source          TEXT    NOT NULL,              -- mock | api
    run_id          TEXT    NOT NULL,
    PRIMARY KEY (business_date, metric, dimension)
);

-- One row per command that wrote to the store.
CREATE TABLE IF NOT EXISTS runs (
    run_id          TEXT    NOT NULL PRIMARY KEY,
    command         TEXT    NOT NULL,              -- load | pull | kpi
    business_date   TEXT,                          -- NULL for a kpi run over a period
    started_at      TEXT    NOT NULL,
    finished_at     TEXT,
    files_read      TEXT    NOT NULL DEFAULT '[]', -- JSON array of file names
    rows_written    INTEGER NOT NULL DEFAULT 0,
    warnings_total  INTEGER NOT NULL DEFAULT 0,
    result          TEXT    NOT NULL,              -- ok | failed
    message         TEXT    NOT NULL DEFAULT ''
);

-- The engine's warnings.json for the run that loaded a date (warnings carry no date of their own).
CREATE TABLE IF NOT EXISTS warnings (
    run_id          TEXT    NOT NULL,
    seq             INTEGER NOT NULL,
    business_date   TEXT    NOT NULL,              -- the date that run loaded
    kind            TEXT    NOT NULL,              -- duplicate | bad_date | bad_amount | ...
    source_file     TEXT    NOT NULL DEFAULT '',
    source_row      INTEGER,
    reason          TEXT    NOT NULL DEFAULT '',
    PRIMARY KEY (run_id, seq)
);

-- KPI history, written by recon.kpi (Dani). One row per period, KPI and dimension
-- ('' for a single value; the category name for a top-10 row).
CREATE TABLE IF NOT EXISTS kpi_values (
    period_type     TEXT    NOT NULL,              -- day | week | month
    period_start    TEXT    NOT NULL,
    period_end      TEXT    NOT NULL,
    kpi_id          TEXT    NOT NULL,              -- e.g. fin.revenue (docs/contracts/kpi.md)
    dimension       TEXT    NOT NULL DEFAULT '',
    value           REAL,                          -- NULL when status = no_data
    unit            TEXT    NOT NULL,
    status          TEXT    NOT NULL,              -- ok | partial | no_data
    source          TEXT    NOT NULL,              -- files | internal | mixed
    computed_at     TEXT    NOT NULL,
    PRIMARY KEY (period_type, period_start, kpi_id, dimension)
);

-- Enterprise totals per day over the marketplaces with data.
CREATE VIEW IF NOT EXISTS v_daily AS
SELECT business_date,
       COUNT(CASE WHEN status = 'ok' THEN 1 END) AS marketplaces_ok,
       COUNT(CASE WHEN status IN ('missing', 'stale', 'unknown') THEN 1 END) AS marketplaces_no_data,
       SUM(CASE WHEN status = 'ok' THEN gross_cents END)          AS gross_cents,
       SUM(CASE WHEN status = 'ok' THEN refunds_cents END)        AS refunds_cents,
       SUM(CASE WHEN status = 'ok' THEN revenue_cents END)        AS revenue_cents,
       SUM(CASE WHEN status = 'ok' THEN fees_cents END)           AS fees_cents,
       SUM(CASE WHEN status = 'ok' THEN orders END)               AS orders
FROM pulse_daily
GROUP BY business_date;

-- ISO weeks (Monday to Sunday) per marketplace. Customers are left out on purpose: daily counts
-- don't add up to distinct buyers over a week; count those from transactions.
CREATE VIEW IF NOT EXISTS v_weekly AS
SELECT week_start,
       date(week_start, '+6 days')                                AS week_end,
       marketplace,
       COUNT(*)                                                   AS days_loaded,
       COUNT(CASE WHEN status = 'ok' THEN 1 END) AS days_ok,
       SUM(CASE WHEN status = 'ok' THEN gross_cents END)          AS gross_cents,
       SUM(CASE WHEN status = 'ok' THEN refunds_cents END)        AS refunds_cents,
       SUM(CASE WHEN status = 'ok' THEN revenue_cents END)        AS revenue_cents,
       SUM(CASE WHEN status = 'ok' THEN fees_cents END)           AS fees_cents,
       SUM(CASE WHEN status = 'ok' THEN orders END)               AS orders
FROM (SELECT *, date(business_date, '-6 days', 'weekday 1') AS week_start  -- sqlite: Monday on or before
      FROM pulse_daily)
GROUP BY week_start, marketplace;

-- Calendar months per marketplace. Same rules as v_weekly.
CREATE VIEW IF NOT EXISTS v_monthly AS
SELECT substr(business_date, 1, 7)                                AS month,
       marketplace,
       COUNT(*)                                                   AS days_loaded,
       COUNT(CASE WHEN status = 'ok' THEN 1 END) AS days_ok,
       SUM(CASE WHEN status = 'ok' THEN gross_cents END)          AS gross_cents,
       SUM(CASE WHEN status = 'ok' THEN refunds_cents END)        AS refunds_cents,
       SUM(CASE WHEN status = 'ok' THEN revenue_cents END)        AS revenue_cents,
       SUM(CASE WHEN status = 'ok' THEN fees_cents END)           AS fees_cents,
       SUM(CASE WHEN status = 'ok' THEN orders END)               AS orders
FROM pulse_daily
GROUP BY substr(business_date, 1, 7), marketplace;
