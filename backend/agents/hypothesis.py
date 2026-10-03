"""
Deterministic hypothesis / correlation testing for the Data Scientist Agent.
Engineers per-customer features and tests which correlate with total spend,
using Pearson correlation with significance (p-values) via scipy.
The LLM interprets; it never computes the statistics.
"""
import numpy as np
from scipy import stats
from sqlalchemy import text
from database import aw_engine


def get_customer_features() -> dict:
    """
    Build per-customer features from AdventureWorks:
      - num_orders: how many orders the customer placed
      - avg_order_value: their average order total
      - tenure_days: span between first and last order
      - total_spend: target variable (sum of order totals)
    Returns columns + rows.
    """
    query = text("""
        SELECT
            customerid,
            COUNT(*) AS num_orders,
            ROUND(AVG(totaldue)::numeric, 2) AS avg_order_value,
            EXTRACT(DAY FROM (MAX(orderdate) - MIN(orderdate))) AS tenure_days,
            ROUND(SUM(totaldue)::numeric, 2) AS total_spend
        FROM sales.salesorderheader
        GROUP BY customerid
        HAVING COUNT(*) >= 1;
    """)
    with aw_engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    columns = ["customerid", "num_orders", "avg_order_value", "tenure_days", "total_spend"]
    data = [[float(v) if v is not None else 0.0 for v in row] for row in rows]
    return {"columns": columns, "rows": data}


def correlate_with_target(data: dict, target: str = "total_spend") -> dict:
    """
    Compute Pearson correlation (with p-values) between each feature and the target.
    Excludes the target itself and any ID columns.
    """
    columns = data["columns"]
    rows = data["rows"]

    if len(rows) < 10:
        return {"error": "Not enough rows for correlation analysis (need >= 10)."}

    arr = np.array(rows, dtype=float)
    col_idx = {c: i for i, c in enumerate(columns)}

    if target not in col_idx:
        return {"error": f"Target '{target}' not found."}

    target_vals = arr[:, col_idx[target]]

    # Features = everything except the target and obvious ID columns
    exclude = {target, "customerid"}
    results = []
    for c in columns:
        if c in exclude:
            continue
        feature_vals = arr[:, col_idx[c]]
        # Pearson correlation + p-value
        r, p = stats.pearsonr(feature_vals, target_vals)
        results.append({
            "feature": c,
            "correlation": round(float(r), 4),
            "p_value": round(float(p), 6),
            "significant": bool(p < 0.05),
            "strength": _strength_label(abs(r)),
        })

    # Sort by absolute correlation, strongest first
    results.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return {
        "target": target,
        "n_customers": len(rows),
        "features_tested": len(results),
        "correlations": results,
    }


def _strength_label(abs_r: float) -> str:
    if abs_r >= 0.7:
        return "strong"
    if abs_r >= 0.4:
        return "moderate"
    if abs_r >= 0.2:
        return "weak"
    return "negligible"
