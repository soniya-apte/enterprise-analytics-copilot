"""
Deterministic statistics layer for the Analytics Agent.
Computes precise metrics from query results using pandas,
so numerical claims never depend on the LLM's arithmetic.
"""
import pandas as pd


def compute_stats(columns: list, rows: list) -> dict:
    """
    Given columns and rows (from the Data Agent), compute descriptive stats.
    Returns a dict of computed metrics that the LLM will later interpret.
    """
    if not rows:
        return {"error": "No data to analyze.", "summary": {}}

    df = pd.DataFrame(rows, columns=columns)

    # Identify numeric columns (coerce where possible)
    numeric_cols = []
    for col in df.columns:
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.notna().sum() > 0:
            df[col] = coerced
            numeric_cols.append(col)

    summary = {
        "row_count": len(df),
        "columns": list(df.columns),
        "numeric_columns": numeric_cols,
        "metrics": {},
    }

    # Per-numeric-column descriptive stats
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        summary["metrics"][col] = {
            "total": round(float(series.sum()), 2),
            "mean": round(float(series.mean()), 2),
            "min": round(float(series.min()), 2),
            "max": round(float(series.max()), 2),
        }

    # If there are at least 2 rows and a numeric column, compute first->last change
    if len(df) >= 2 and numeric_cols:
        primary = numeric_cols[0]
        first_val = float(df[primary].iloc[0])
        last_val = float(df[primary].iloc[-1])
        change = last_val - first_val
        pct_change = (change / first_val * 100) if first_val != 0 else None
        summary["first_to_last"] = {
            "column": primary,
            "first": round(first_val, 2),
            "last": round(last_val, 2),
            "change": round(change, 2),
            "pct_change": round(pct_change, 2) if pct_change is not None else None,
        }

    return summary
