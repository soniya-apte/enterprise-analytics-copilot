"""Compare context strategies by recall: does the agent's schema context contain
every table that the gold SQL needs? (Free - no LLM calls.)

Usage (run from backend/):  python -m rag.compare_strategies
"""
from agents.schema_context import SCHEMA_CONTEXT
from benchmark.questions import QUESTIONS
from rag.store import TABLE_RE, retrieve

STATIC = {f"{s}.{t}" for s, t in TABLE_RE.findall(SCHEMA_CONTEXT)}   # tables in the hand-written context
CORE = {"sales.salesorderheader", "sales.salesorderdetail"}

needed = {q["id"]: {f"{s}.{t}" for s, t in TABLE_RE.findall(q["gold_sql"])} for q in QUESTIONS}
ranked = {q["id"]: [r["table"] for r in retrieve(q["question"], k=10)] for q in QUESTIONS}

strategies = {
    "static context only (= baseline)": lambda r: STATIC,
    "pure top-6":                       lambda r: set(r[:6]),
    "pure top-10":                      lambda r: set(r[:10]),
    "core 2 tables + top-6":            lambda r: CORE | set(r[:6]),
    "static context + top-4":           lambda r: STATIC | set(r[:4]),
    "static context + top-6":           lambda r: STATIC | set(r[:6]),
}

print(f"Hand-written context covers {len(STATIC)} tables: {sorted(STATIC)}\n")
print(f"{'strategy':<36}{'recall':>8}   avg tables in context")
for name, select in strategies.items():
    hits = sum(needed[i] <= select(ranked[i]) for i in needed)
    avg = sum(len(select(ranked[i])) for i in needed) / len(needed)
    print(f"{name:<36}{hits:>4}/{len(needed)}   {avg:5.1f}")

for name in ("static context only (= baseline)", "static context + top-4"):
    print(f"\nMisses for '{name}':")
    for q in QUESTIONS:
        missing = needed[q["id"]] - strategies[name](ranked[q["id"]])
        if missing:
            print(f"   {q['id']}: missing {sorted(missing)}")
