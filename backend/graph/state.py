"""Shared state that flows through the LangGraph pipeline.

Each agent (node) reads the fields it needs and returns the fields it adds.
LangGraph merges those returned fields into this state automatically.
"""
from typing import TypedDict


class AnalyticsState(TypedDict, total=False):
    # --- Input ---
    question: str             # the user's business question

    # --- Agent 1: Planner ---
    plan: dict                # full plan from create_plan()
    analysis_type: str        # descriptive | diagnostic | predictive | comparative (used for routing)
    uses_live_stream: bool    # True if the question is about the live stream's alerts/anomalies

    # --- Agent 2: Data Agent + executor ---
    sql: str                  # the generated SQL query
    sql_explanation: str      # one-sentence description of the query
    query_result: dict        # execute_sql() output: success, error, columns, rows, row_count
    sql_attempts: int         # how many times we've tried (for the self-correction loop)

    # --- Agent 3: Analytics ---
    analysis: dict            # insights from analyze()

    # --- Agent 4: Data Scientist (only for some question types) ---
    data_science: dict        # forecast / anomaly / driver results

    # --- Agent 5: Reporting ---
    report: dict              # executive summary, takeaways, chart specs

    # --- Agent 6: Evaluation ---
    evaluation: dict          # score (0-100) and critique

    # --- Bookkeeping ---
    usage: list               # token usage per LLM call (for cost tracking)
    errors: list              # any errors along the way
