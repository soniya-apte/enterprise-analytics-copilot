"""LangGraph nodes: thin wrappers that connect existing agents to the shared state.

Pattern for every node: read from state -> call the agent -> return only new fields.
"""
from graph.state import AnalyticsState
from agents.planner import create_plan
from agents.data_agent import generate_sql
from agents.sql_executor import execute_sql
from agents.analytics_agent import analyze
from agents.data_scientist_agent import forecast_revenue, analyze_anomalies
from agents.stream_monitor import get_stream_anomalies
from agents.reporting_agent import generate_report
from agents.evaluation_agent import evaluate


def _record_usage(state: AnalyticsState, agent: str, result: dict) -> list:
    """Pull the _usage info off an agent result and add it to the running list."""
    usage = result.pop("_usage", None) if isinstance(result, dict) else None
    log = list(state.get("usage", []))
    if usage:
        log.append({"agent": agent, **usage})
    return log


def has_data(result: dict) -> bool:
    """True only if the query succeeded AND returned at least one non-NULL value.

    Note: aggregates like SUM() over zero rows return one row containing NULL,
    so checking row_count alone is not enough.
    """
    if not result.get("success"):
        return False
    return any(v is not None for row in result.get("rows", []) for v in row)


def planner_node(state: AnalyticsState) -> dict:
    """Agent 1: turn the question into a plan and pick the analysis type."""
    plan = create_plan(state["question"])
    return {
        "plan": plan,
        "analysis_type": plan.get("analysis_type", "descriptive"),
        "uses_live_stream": bool(plan.get("uses_live_stream", False)),
        "usage": _record_usage(state, "planner", plan),
    }


def data_node(state: AnalyticsState) -> dict:
    """Agent 2: generate SQL, then validate and run it (read-only).

    On a retry, the previous SQL and what went wrong are sent back to the
    model so it can correct itself (self-correction loop).
    """
    attempts = state.get("sql_attempts", 0)
    feedback = None
    prev = state.get("query_result")
    if attempts > 0 and prev is not None:
        problem = prev.get("error") or "The query ran but returned no data (0 rows or only NULL values)."
        prev_sql = state.get("sql", "")
        feedback = (f"Previous SQL:\n{prev_sql}\n\nProblem: {problem}\n"
                    "Check table names, joins, filters and dates. "
                    "Do NOT change what the question is asking for.")

    sql_out = generate_sql(state["question"], feedback)
    usage = _record_usage(state, "data_agent", sql_out)
    sql = sql_out.get("sql", "")
    result = execute_sql(sql)

    errors = list(state.get("errors", []))
    if not result["success"]:
        errors.append(f"SQL attempt {attempts + 1} failed: {result['error']}")
    elif not has_data(result):
        errors.append(f"SQL attempt {attempts + 1} returned no data (0 rows or only NULLs)")

    return {
        "sql": sql,
        "sql_explanation": sql_out.get("explanation", ""),
        "query_result": result,
        "sql_attempts": attempts + 1,
        "usage": usage,
        "errors": errors,
    }


def analytics_node(state: AnalyticsState) -> dict:
    """Agent 3: compute stats on the query results and interpret them."""
    r = state["query_result"]
    insights = analyze(state["question"], r["columns"], r["rows"])
    return {
        "analysis": insights,
        "usage": _record_usage(state, "analytics", insights),
    }


def data_science_node(state: AnalyticsState) -> dict:
    """Agent 4: run the model that fits the question type.

    predictive -> revenue forecast; diagnostic -> monthly anomaly detection.
    """
    if state.get("uses_live_stream"):
        result = get_stream_anomalies(days=30)
        kind = "live_stream_anomalies"
    elif state.get("analysis_type") == "predictive":
        result = forecast_revenue(periods_ahead=3)
        kind = "forecast"
    else:
        result = analyze_anomalies(dimension="month")
        kind = "anomalies"
    return {
        "data_science": {"kind": kind, "result": result},
        "usage": _record_usage(state, "data_scientist", result),
    }


def reporting_node(state: AnalyticsState) -> dict:
    """Agent 5: combine everything available into an executive report."""
    r = state["query_result"]
    context = {
        "sql_explanation": state.get("sql_explanation"),
        "data": {"columns": r["columns"], "rows": r["rows"]},
        "analytics": state.get("analysis"),
    }
    if state.get("data_science"):
        context["data_science"] = state["data_science"]
        if state["data_science"].get("kind") == "live_stream_anomalies":
            res = state["data_science"].get("result", {})
            context["important_caveats"] = [res.get("detector_note"), res.get("data_quality_note")]
            context["note_to_reporter"] = (
                "For this question, the PRIMARY evidence is data_science.result: the live-stream "
                "anomaly detector's flags. Name specific flagged dates and territories (with revenue "
                "vs. normal baseline). Lead with the important_caveats, stated plainly. Attribute EVERY "
                "finding to its source: 'SQL query' (solid facts) or 'live-stream detector' "
                "(low-precision leads). Do not invent causes that are not supported by the data."
            )
    if state.get("errors"):
        context["pipeline_errors"] = state["errors"]
    report = generate_report(state["question"], context)
    return {
        "report": report,
        "usage": _record_usage(state, "reporting", report),
    }


def evaluation_node(state: AnalyticsState) -> dict:
    """Agent 6: critique the SQL and report, and score the answer 0-100."""
    r = state["query_result"]
    try:
        result = evaluate(state["question"], state["sql"], r["columns"], r["rows"],
                          state["report"], state.get("data_science"))
    except Exception as e:   # never lose a finished report because the evaluator failed
        errors = list(state.get("errors", [])) + [f"Evaluation failed: {e}"]
        return {"evaluation": {"overall_score": None, "summary": f"Evaluation failed: {e}"},
                "errors": errors}
    return {
        "evaluation": result,
        "usage": _record_usage(state, "evaluation", result),
    }
