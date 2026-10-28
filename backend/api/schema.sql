-- API layer: every question asked through /ask, with its answer and diagnostics.
CREATE TABLE IF NOT EXISTS question_history (
    id               SERIAL PRIMARY KEY,
    asked_at         TIMESTAMPTZ   NOT NULL DEFAULT now(),
    question         TEXT          NOT NULL,
    analysis_type    TEXT,
    uses_live_stream BOOLEAN,
    sql_text         TEXT,
    sql_attempts     INTEGER,
    sql_success      BOOLEAN,
    row_count        INTEGER,
    summary          TEXT,
    overall_score    INTEGER,          -- Evaluation Agent score (NULL if evaluation failed)
    cost_usd         NUMERIC(10,5),    -- estimated LLM cost of this run
    duration_ms      INTEGER,          -- wall-clock time of the whole pipeline
    errors           JSONB,            -- problems logged along the way
    response         JSONB             -- the full JSON response returned to the caller
);
CREATE INDEX IF NOT EXISTS question_history_asked_at_idx ON question_history (asked_at DESC);
