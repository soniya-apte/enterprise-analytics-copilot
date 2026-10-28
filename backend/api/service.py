"""API service: run the pipeline, make the result JSON-safe, and store it."""
import json
import time
from datetime import date, datetime
from decimal import Decimal

import numpy as np
from sqlalchemy import text

from database import app_engine
from graph.pipeline import estimate_cost, run_pipeline


def to_jsonable(obj):
    """Convert Decimals, dates and numpy values (anywhere in a nested structure) to plain JSON types."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def ask(question: str) -> dict:
    """Run one question through the full pipeline, store it, and return the response."""
    start = time.perf_counter()
    final = run_pipeline(question, verbose=False)
    duration_ms = int((time.perf_counter() - start) * 1000)

    r = final.get("query_result", {})
    report = final.get("report", {})
    usage = final.get("usage", [])
    response = to_jsonable({
        "question": question,
        "answer": {
            "summary": report.get("executive_summary"),
            "key_takeaways": report.get("key_takeaways"),
            "recommendations": report.get("recommendations"),
            "chart_specs": report.get("chart_specs"),
            "confidence_note": report.get("confidence_note"),
        },
        "data": {"columns": r.get("columns", []), "rows": r.get("rows", []), "row_count": r.get("row_count")},
        "sql": {"query": final.get("sql"), "explanation": final.get("sql_explanation"),
                "attempts": final.get("sql_attempts"), "success": r.get("success")},
        "routing": {"analysis_type": final.get("analysis_type"),
                    "uses_live_stream": final.get("uses_live_stream"),
                    "data_science": (final.get("data_science") or {}).get("kind")},
        "analysis": final.get("analysis"),
        "data_science": final.get("data_science"),
        "evaluation": final.get("evaluation"),
        "diagnostics": {"errors": final.get("errors", []), "llm_calls": len(usage),
                        "cost_usd": round(estimate_cost(usage), 5), "duration_ms": duration_ms},
    })
    response["id"] = _save(response)
    return response


def _save(resp: dict) -> int:
    score = (resp.get("evaluation") or {}).get("overall_score")
    with app_engine.begin() as c:
        return c.execute(text("""
            INSERT INTO question_history
                (question, analysis_type, uses_live_stream, sql_text, sql_attempts, sql_success,
                 row_count, summary, overall_score, cost_usd, duration_ms, errors, response)
            VALUES (:question, :analysis_type, :uses_live_stream, :sql_text, :sql_attempts, :sql_success,
                    :row_count, :summary, :overall_score, :cost_usd, :duration_ms,
                    CAST(:errors AS jsonb), CAST(:response AS jsonb))
            RETURNING id
        """), {
            "question": resp["question"],
            "analysis_type": resp["routing"]["analysis_type"],
            "uses_live_stream": resp["routing"]["uses_live_stream"],
            "sql_text": resp["sql"]["query"],
            "sql_attempts": resp["sql"]["attempts"],
            "sql_success": resp["sql"]["success"],
            "row_count": resp["data"]["row_count"],
            "summary": resp["answer"]["summary"],
            "overall_score": int(score) if isinstance(score, (int, float)) else None,
            "cost_usd": resp["diagnostics"]["cost_usd"],
            "duration_ms": resp["diagnostics"]["duration_ms"],
            "errors": json.dumps(resp["diagnostics"]["errors"]),
            "response": json.dumps(resp),
        }).scalar()


def history(limit: int = 20) -> list:
    """Most recent questions (summary fields only)."""
    with app_engine.connect() as c:
        rows = c.execute(text("""
            SELECT id, asked_at, question, analysis_type, uses_live_stream, sql_success,
                   overall_score, cost_usd, duration_ms
            FROM question_history ORDER BY asked_at DESC LIMIT :limit
        """), {"limit": limit}).mappings().all()
    return [to_jsonable(dict(r)) for r in rows]


def get_answer(qid: int) -> dict | None:
    """The full stored response for one past question."""
    with app_engine.connect() as c:
        resp = c.execute(text("SELECT response FROM question_history WHERE id = :id"), {"id": qid}).scalar()
    return resp
