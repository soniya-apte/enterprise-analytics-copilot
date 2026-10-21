-- Time-series ingestion layer: tables in the analytics_copilot (app) database.
-- v2: split by sales channel ('online' = continuous daily stream, 'reseller' = bulk batch orders).

-- 1) The "live" stream: one row per day per territory per channel.
CREATE TABLE IF NOT EXISTS stream_daily_sales (
    sale_date      DATE          NOT NULL,
    territory_id   INTEGER       NOT NULL,
    channel        TEXT          NOT NULL,   -- online | reseller
    territory_name TEXT          NOT NULL,
    region_group   TEXT          NOT NULL,
    order_count    INTEGER       NOT NULL,
    revenue        NUMERIC(14,2) NOT NULL,
    ingested_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (sale_date, territory_id, channel)
);

-- 2) Ground truth: every anomaly the simulator injected (used only for evaluation).
CREATE TABLE IF NOT EXISTS injected_anomalies (
    anomaly_id       SERIAL PRIMARY KEY,
    sale_date        DATE          NOT NULL,
    territory_id     INTEGER       NOT NULL,
    channel          TEXT          NOT NULL,
    anomaly_type     TEXT          NOT NULL,   -- spike | drop | outage
    original_revenue NUMERIC(14,2) NOT NULL,
    injected_revenue NUMERIC(14,2) NOT NULL,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- 3) Watermark: how far the replay has progressed (each run continues from here).
CREATE TABLE IF NOT EXISTS ingestion_state (
    id                 INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    last_ingested_date DATE,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO ingestion_state (id, last_ingested_date)
VALUES (1, NULL) ON CONFLICT (id) DO NOTHING;

-- 4) Detector output: what the streaming anomaly detector flagged.
CREATE TABLE IF NOT EXISTS detected_anomalies (
    sale_date       DATE          NOT NULL,
    territory_id    INTEGER       NOT NULL,
    channel         TEXT          NOT NULL,
    detected_type   TEXT          NOT NULL,   -- spike | drop | outage
    revenue         NUMERIC(14,2) NOT NULL,
    baseline_median NUMERIC(14,2),
    score           NUMERIC(10,2),
    method          TEXT          NOT NULL DEFAULT 'rolling_robust_z',
    detected_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (sale_date, territory_id, channel)
);
