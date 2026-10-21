"""LangGraph nodes: thin wrappers that connect existing agents to the shared state.

Pattern for every node: read from state -> call the agent -> return only new fields.
"""
from graph.state import AnalyticsState
from agents.planner import create_plan
from agents.data_agent import generate_sql
from agents.sql_executor import execute_sql
from agents.analytics_agent import analyze
from agents.data_scientist_agent import forecast_revenue, analyze_anomalies
from agents.reporting_agent import generate_report
from agents.evaluation_agent import evaluate


def _record_usage(state: AnalyticsState, agent: str, result: dict) -> list:
    """Pull the _usage info off an agent result and add it to the running list."""
    usage = result.pop("_usage", None) if isinstance(result, dict) else None
    log = list(state.get("usage", []))
    if usage:
        log.append({"agent": agent, **usage})
    return log


def planner_node(state: AnalyticsState) -> dict:
    """Agent 1: turn the question into a plan and pick the analysis type."""
    plan = create_plan(state["question"])
    return {
        "plan": plan,
        "analysis_type": plan.get("analysis_type", "descriptive"),
        "usage": _record_usage(state, "planner", plan),
    }


def data_node(state: AnalyticsState) -> dict:
    """Agent 2: generate SQL, then validate and run it (read-only)."""
    sql_out = generate_sql(state["question"])
    usage = _record_usage(state, "data_agent", sql_out)
    sql = sql_out.get("sql", "")
    result = execute_sql(sql)
    return {
        "sql": sql,
        "sql_explanation": sql_out.get("explanation", ""),
        "query_result": result,
        "sql_attempts": state.get("sql_attempts", 0) + 1,
        "usage": usage,
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
    if state.get("analysis_type") == "predictive":
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
    report = generate_report(state["question"], context)
    return {
        "report": report,
        "usage": _record_usage(state, "reporting", report),
    }


def evaluation_node(state: AnalyticsState) -> dict:
    """Agent 6: critique the SQL and report, and score the answer 0-100."""
    r = state["query_result"]
    result = evaluate(state["question"], state["sql"], r["columns"], r["rows"], state["report"], state.get("data_science"))
    return {
        "evaluation": result,
        "usage": _record_usage(state, "evaluation", result),
    }
