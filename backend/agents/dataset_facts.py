"""Facts about the dataset that every report should know.

Computed from the database (not hard-coded), once per server process.
Given to the Reporting Agent and the Evaluator so they state these facts
instead of guessing (e.g. "2025 may be incomplete").
"""
from functools import lru_cache

from sqlalchemy import text
from database import aw_engine


@lru_cache(maxsize=1)
def get_dataset_facts() -> dict:
    with aw_engine.connect() as c:
        first, last = c.execute(text(
            "SELECT MIN(orderdate)::date, MAX(orderdate)::date FROM sales.salesorderheader")).one()
        reseller_days, reseller_aov, online_aov = c.execute(text("""
            SELECT COUNT(DISTINCT orderdate::date) FILTER (WHERE NOT onlineorderflag),
                   ROUND(AVG(totaldue) FILTER (WHERE NOT onlineorderflag)),
                   ROUND(AVG(totaldue) FILTER (WHERE onlineorderflag))
            FROM sales.salesorderheader""")).one()
    return {
        "data_coverage": (
            f"Sales orders run from {first} to {last}. Calendar years {first.year} and {last.year} "
            f"are PARTIAL years (not 12 months of data), so year-over-year comparisons involving them "
            f"are not like-for-like. The final month ({last:%Y-%m}) is also incomplete."
        ),
        "reseller_batches": (
            f"Reseller (store) orders arrive in large batches on only {reseller_days} days in the whole "
            f"dataset, typically around month-end, with an average order value of about ${reseller_aov:,.0f} "
            f"(online orders average about ${online_aov:,.0f}). A day with very high total revenue and a high "
            f"average order value is normally a reseller batch day: expected business behaviour, not an anomaly."
        ),
        "revenue_definition": "Order-level revenue uses totaldue, which includes tax and freight.",
    }
