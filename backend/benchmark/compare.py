"""Result-set comparison for the text-to-SQL benchmark (execution accuracy).

Two levels:
  strict  - every gold column (labels AND numbers) appears in the prediction
  lenient - every NUMERIC gold column appears (labels may be formatted differently,
            e.g. 'Linda Mitchell' vs. separate first/last name columns)
Ignored: column names, column order, extra columns, rounding, date formatting.
Rows are checked together (values must stay paired). Row order only counts when
the question asks for it (e.g. "top 5"). For no-data questions, empty/NULL/0 all match.
"""
import re
from datetime import date, datetime
from decimal import Decimal

MONTH_START = re.compile(r"^(\d{4}-\d{2})-01(?:[ t]00:00(?::00)?)?")


def norm(v):
    """Normalize one value so equivalent answers compare equal."""
    if v is None:
        return None
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float, Decimal)):
        return float(v)
    if isinstance(v, datetime):
        v = v.date()
    if isinstance(v, date):
        return v.strftime("%Y-%m") if v.day == 1 else v.isoformat()
    s = str(v).strip().lower()
    m = MONTH_START.match(s)
    return m.group(1) if m else s


def same(a, b) -> bool:
    """Equal values; numbers may differ by rounding (0.01, or 0.01% of the value)."""
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= max(0.01, 1e-4 * max(abs(a), abs(b)))
    return a == b


def _key(x):
    return (x is None, isinstance(x, str), x if isinstance(x, (float, str)) else 0)


def _col_equal(gc, pc, order_matters) -> bool:
    if len(gc) != len(pc):
        return False
    if not order_matters:
        gc, pc = sorted(gc, key=_key), sorted(pc, key=_key)
    return all(same(a, b) for a, b in zip(gc, pc))


def _match(g, p, order_matters, numeric_only) -> bool:
    if len(g) != len(p) or not g:
        return False
    gcols, pcols = list(zip(*g)), list(zip(*p))
    used, mapping = set(), []
    for gi, gc in enumerate(gcols):
        is_numeric = all(isinstance(x, float) or x is None for x in gc)
        found = None
        for pi, pc in enumerate(pcols):
            if pi not in used and _col_equal(gc, pc, order_matters):
                found = pi
                break
        if found is not None:
            used.add(found)
            mapping.append((gi, found))   # matched columns always take part in the pairing check
        elif numeric_only and not is_numeric:
            continue                      # lenient: a label we can't match is allowed (formatted differently)
        else:
            return False
    if not mapping:
        return False
    # Row-wise check on the matched columns, so values must stay correctly paired
    grows = [tuple(r[gi] for gi, _ in mapping) for r in g]
    prows = [tuple(r[pi] for _, pi in mapping) for r in p]
    if not order_matters:
        grows = sorted(grows, key=lambda r: tuple(_key(x) for x in r))
        prows = sorted(prows, key=lambda r: tuple(_key(x) for x in r))
    return all(same(a, b) for gr, pr in zip(grows, prows) for a, b in zip(gr, pr))


def is_no_data(rows) -> bool:
    return len(rows) == 0 or all(v is None or v == 0 for r in rows for v in r)


def compare(gold_rows, pred_rows, order_matters=False) -> dict:
    """Return {'strict': bool, 'lenient': bool, 'reason': str}."""
    g = [[norm(v) for v in r] for r in gold_rows]
    p = [[norm(v) for v in r] for r in pred_rows]
    if is_no_data(g):
        ok = is_no_data(p)
        return {"strict": ok, "lenient": ok,
                "reason": "no-data question" + ("" if ok else ": prediction returned data")}
    strict = _match(g, p, order_matters, numeric_only=False)
    # Lenient also accepts extra rows after the top-N for ranking questions
    p_top = p[:len(g)] if order_matters and len(p) > len(g) else p
    lenient = strict or _match(g, p_top, order_matters, numeric_only=True)
    reason = "match" if strict else ("numbers match, labels differ" if lenient else "mismatch")
    return {"strict": strict, "lenient": lenient, "reason": reason}


if __name__ == "__main__":
    from datetime import date as d
    from benchmark.questions import QUESTIONS
    from agents.sql_executor import execute_sql

    # 1) Every gold result must match itself
    ok = 0
    for q in QUESTIONS:
        rows = execute_sql(q["gold_sql"])["rows"]
        ok += compare(rows, rows, q["order_matters"])["strict"]
    print(f"Gold vs. itself: {ok}/{len(QUESTIONS)} strict matches (expect {len(QUESTIONS)})")

    # 2) Hand-made cases with known answers: (description, gold, pred, order_matters, expect_strict, expect_lenient)
    cases = [
        ("reordered + extra column", [["Bikes", 100.0]], [[7, 100.004, "bikes"]], False, True, True),
        ("date vs 'YYYY-MM' label", [["2024-01", 5.0]], [[d(2024, 1, 1), 5.0]], False, True, True),
        ("name split into 2 columns", [["Linda Mitchell", 9.0]], [["Linda", "Mitchell", 9.0]], True, False, True),
        ("wrong number (5% off)", [[2022, 100.0]], [[2022, 105.0]], False, False, False),
        ("wrong pairing of rows", [["A", 1.0], ["B", 2.0]], [["A", 2.0], ["B", 1.0]], False, False, False),
        ("no data: empty result", [[None]], [], False, True, True),
        ("no data: zero", [[None]], [[0]], False, True, True),
        ("no data: but returned data", [[None]], [[123.0]], False, False, False),
        ("top-1 but returned all rows", [["2025-04", 5.8]], [["2025-04", 5.8], ["2024-05", 5.0]], True, False, True),
    ]
    passed = 0
    for desc, g, p, om, es, el in cases:
        r = compare(g, p, om)
        good = (r["strict"], r["lenient"]) == (es, el)
        passed += good
        print(f"  {'PASS' if good else 'FAIL'}  {desc:<30} -> strict={r['strict']}, lenient={r['lenient']}")
    print(f"Hand-made cases: {passed}/{len(cases)} passed")
