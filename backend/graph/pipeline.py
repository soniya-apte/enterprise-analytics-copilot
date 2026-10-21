"""The LangGraph pipeline: wires the six agent nodes into one automated workflow."""
import sys
from langgraph.graph import StateGraph, START, END

from graph.state import AnalyticsState
from graph.nodes import (
    has_data,
    planner_node, data_node, analytics_node,
    data_science_node, reporting_node, evaluation_node,
)

# Claude Haiku 4.5 pricing (USD per million tokens) - used to estimate cost per run
PRICE_IN, PRICE_OUT = 1.00, 5.00


# ---------- Routing functions (decide which node runs next) ----------

MAX_SQL_ATTEMPTS = 3


def route_after_data(state: AnalyticsState) -> str:
    """Self-correction loop: continue if we got data, retry if not, report honestly after 3 tries."""
    r = state["query_result"]
    if has_data(r):
        return "analytics"
    if state.get("sql_attempts", 0) < MAX_SQL_ATTEMPTS:
        return "retry"
    return "give_up"


def route_after_analytics(state: AnalyticsState) -> str:
    """Only predictive and diagnostic questions need the Data Scientist."""
    if state.get("analysis_type") in ("predictive", "diagnostic"):
        return "data_science"
    return "reporting"


# ---------- Build the graph ----------

def build_graph():
    g = StateGraph(AnalyticsState)

    g.add_node("planner", planner_node)
    g.add_node("data", data_node)
    g.add_node("analytics", analytics_node)
    g.add_node("data_science", data_science_node)
    g.add_node("reporting", reporting_node)
    g.add_node("evaluation", evaluation_node)

    g.add_edge(START, "planner")
    g.add_edge("planner", "data")
    g.add_conditional_edges("data", route_after_data,
                            {"analytics": "analytics", "retry": "data", "give_up": "reporting"})
    g.add_conditional_edges("analytics", route_after_analytics,
                            {"data_science": "data_science", "reporting": "reporting"})
    g.add_edge("data_science", "reporting")
    g.add_edge("reporting", "evaluation")
    g.add_edge("evaluation", END)

    return g.compile()


def estimate_cost(usage: list) -> float:
    tin = sum(u["input_tokens"] for u in usage)
    tout = sum(u["output_tokens"] for u in usage)
    return tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT


def run_pipeline(question: str, verbose: bool = True) -> dict:
    """Run one question through the whole graph and return the final state."""
    app = build_graph()
    state: AnalyticsState = {"question": question, "sql_attempts": 0, "usage": [], "errors": []}
    for step in app.stream(state, stream_mode="updates"):
        for node_name, update in step.items():
            if verbose:
                print(f"  ✓ {node_name}")
            state.update(update)
    return state


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What will our monthly revenue look like over the next 3 months?"
    print(f"Question: {q}\nRunning pipeline:")
    final = run_pipeline(q)

    r = final.get("query_result", {})
    print("\n--- RESULT ---")
    print("Analysis type:", final.get("analysis_type"))
    print("SQL success:", r.get("success"), "| rows:", r.get("row_count"), "| error:", r.get("error"))
    print("SQL attempts:", final.get("sql_attempts"), "| errors:", final.get("errors"))
    if "report" in final:
        print("Report keys:", list(final["report"].keys()))
        print("Summary:", final["report"].get("executive_summary", "(no executive_summary key)"))
    if "evaluation" in final:
        ev = final["evaluation"]
        print("Evaluation keys:", list(ev.keys()))
        print("Score:", ev.get("score", ev.get("overall_score", "(see keys)")))
    print(f"LLM calls: {len(final['usage'])} | Est. cost: ${estimate_cost(final['usage']):.4f}")
