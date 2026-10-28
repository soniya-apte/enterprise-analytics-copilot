"""Text-to-SQL benchmark runner: execution accuracy, single-shot vs. self-correction.

For each question, attempt 1 IS the single-shot answer. If it errors or returns no
data, the self-correction loop retries with feedback (up to 3 attempts). Both methods
are scored on the same first attempt (a paired comparison), and the cost of
self-correction is only paid when it is actually used.

Usage (run from backend/):
    python -m benchmark.run --runs 1 --ids q01,q02,q23 --label pilot   # quick pilot
    python -m benchmark.run --runs 3 --label baseline                  # full benchmark
"""
import argparse
import json
import os
from collections import defaultdict
from datetime import datetime

from agents.sql_executor import execute_sql
from benchmark.compare import compare
from benchmark.questions import QUESTIONS
from graph.nodes import data_node, has_data

MAX_ATTEMPTS = 3
PRICE_IN, PRICE_OUT = 1.00, 5.00   # Claude Haiku 4.5, USD per million tokens
RESULTS_DIR = "benchmark/results"
FAILED = {"strict": False, "lenient": False, "reason": "SQL error"}


def run_question(q: dict, run: int) -> dict:
    gold_rows = execute_sql(q["gold_sql"], row_limit=1000)["rows"]
    state = {"question": q["question"], "sql_attempts": 0, "usage": [], "errors": []}
    attempts, first = [], None
    while True:
        state.update(data_node(state))
        r = state["query_result"]
        if first is None:
            first = r
        attempts.append({"sql": state["sql"], "success": r["success"], "error": r["error"],
                         "rows": r.get("row_count")})
        if has_data(r) or state["sql_attempts"] >= MAX_ATTEMPTS:
            break
    final = state["query_result"]
    single = compare(gold_rows, first["rows"], q["order_matters"]) if first["success"] else FAILED
    corrected = compare(gold_rows, final["rows"], q["order_matters"]) if final["success"] else FAILED
    tin = sum(u["input_tokens"] for u in state["usage"])
    tout = sum(u["output_tokens"] for u in state["usage"])
    return {
        "id": q["id"], "run": run, "difficulty": q["difficulty"], "tags": q["tags"],
        "single_strict": single["strict"], "single_lenient": single["lenient"],
        "corrected_strict": corrected["strict"], "corrected_lenient": corrected["lenient"],
        "reason": corrected["reason"], "n_attempts": len(attempts), "attempts": attempts,
        "cost": tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT,
    }


def summarize(results: list) -> None:
    def pct(rows, key):
        return 100 * sum(r[key] for r in rows) / len(rows) if rows else 0.0

    n_q = len({r["id"] for r in results})
    n_runs = len({r["run"] for r in results})
    print(f"\n=== Execution accuracy ({n_q} questions x {n_runs} runs = {len(results)} answers) ===")
    print(f"{'':<22}{'strict':>8}{'lenient':>9}")
    for label, m in (("Single-shot", "single"), ("+ self-correction", "corrected")):
        print(f"{label:<22}{pct(results, m + '_strict'):>7.1f}%{pct(results, m + '_lenient'):>8.1f}%")

    print("\nBy difficulty (with self-correction, strict):")
    for diff in ("easy", "medium", "hard"):
        rows = [r for r in results if r["difficulty"] == diff]
        if rows:
            print(f"   {diff:<7} {pct(rows, 'corrected_strict'):5.1f}%  ({len(rows)} answers)")

    per_q = defaultdict(list)
    for r in results:
        per_q[r["id"]].append(r)
    misses = {qid: rs for qid, rs in per_q.items() if not all(x["corrected_strict"] for x in rs)}
    print(f"\nQuestions not always correct (strict): {len(misses)}/{n_q}")
    for qid, rs in sorted(misses.items()):
        ok = sum(x["corrected_strict"] for x in rs)
        print(f"   {qid}: {ok}/{len(rs)} correct | last reason: {rs[-1]['reason']}")
    print(f"\nTotal cost: ${sum(r['cost'] for r in results):.4f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Run the text-to-SQL benchmark.")
    p.add_argument("--runs", type=int, default=1, help="how many times to run each question")
    p.add_argument("--ids", default="", help="comma-separated question ids (default: all)")
    p.add_argument("--label", default="baseline", help="name for the results file")
    args = p.parse_args()

    wanted = set(args.ids.split(",")) if args.ids else None
    qs = [q for q in QUESTIONS if not wanted or q["id"] in wanted]
    results = []
    for run in range(1, args.runs + 1):
        for q in qs:
            res = run_question(q, run)
            results.append(res)
            mark = lambda m: "Y" if res[m + "_strict"] else ("~" if res[m + "_lenient"] else "N")
            print(f"run {run}  {q['id']}  single={mark('single')}  corrected={mark('corrected')}  "
                  f"attempts={res['n_attempts']}")
    summarize(results)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = f"{RESULTS_DIR}/{args.label}_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Saved detailed results to backend/{path}")
