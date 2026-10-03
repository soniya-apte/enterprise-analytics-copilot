"""
Deterministic anomaly detection for the Data Scientist Agent.
Generic core: flags outliers in any labeled numeric series using
z-score and IQR methods. Specific data feeders (by region, by month)
supply the series. The LLM later interprets; it never computes scores.
"""
import numpy as np
from sqlalchemy import text
from database import aw_engine


def detect_anomalies(series: list, z_threshold: float = 2.0) -> dict:
    """
    Detect outliers in a labeled numeric series.
    `series` is a list of (label, value).
    Flags points whose z-score exceeds z_threshold, and reports IQR outliers too.
    """
    if len(series) < 4:
        return {"error": "Not enough data points for anomaly detection (need >= 4)."}

    labels = [s[0] for s in series]
    values = np.array([float(s[1]) for s in series])

    mean = float(values.mean())
    std = float(values.std())

    # Z-score method
    anomalies = []
    for label, val in zip(labels, values):
        z = (val - mean) / std if std > 0 else 0.0
        if abs(z) >= z_threshold:
            anomalies.append({
                "label": label,
                "value": round(float(val), 2),
                "z_score": round(float(z), 2),
                "direction": "high" if z > 0 else "low",
            })

    # IQR method (for cross-checking)
    q1 = float(np.percentile(values, 25))
    q3 = float(np.percentile(values, 75))
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    return {
        "n_points": len(series),
        "mean": round(mean, 2),
        "std": round(std, 2),
        "z_threshold": z_threshold,
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "iqr_bounds": {"lower": round(lower_bound, 2), "upper": round(upper_bound, 2)},
    }


def get_sales_by_region() -> list:
    """Total revenue per sales territory (region)."""
    query = text("""
        SELECT t.name AS region,
               ROUND(SUM(soh.totaldue)::numeric, 2) AS revenue
        FROM sales.salesorderheader soh
        JOIN sales.salesterritory t ON soh.territoryid = t.territoryid
        GROUP BY t.name
        ORDER BY revenue DESC;
    """)
    with aw_engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return [(r[0], float(r[1])) for r in rows]


def get_sales_by_month() -> list:
    """Total revenue per month."""
    query = text("""
        SELECT DATE_TRUNC('month', orderdate) AS month,
               ROUND(SUM(totaldue)::numeric, 2) AS revenue
        FROM sales.salesorderheader
        GROUP BY month
        ORDER BY month;
    """)
    with aw_engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return [(r[0].strftime("%Y-%m"), float(r[1])) for r in rows]
