"""Streaming anomaly detector.

For each day x territory, compares revenue only against that territory's
PREVIOUS 28 days (no look-ahead), using robust statistics:
  - spike / drop: modified z-score of log(revenue) vs. the territory's recent
    non-zero days (log scale, because the anomalies are multiplicative: x4, x0.1)
  - outage: a zero-revenue day in a territory that usually sells (>= 80% of days)

Usage (run from backend/):
    python -m ingestion.detector       # scan the whole stream ingested so far
"""
import argparse
from datetime import timedelta

import numpy as np
import pandas as pd
from sqlalchemy import text
from database import app_engine

WINDOW_DAYS = 28        # trailing baseline window
Z_THRESHOLD = 3.5       # standard cut-off for the modified z-score (Iglewicz & Hoaglin)
MIN_ACTIVE_DAYS = 5     # need at least this many non-zero days to judge a spike/drop
MIN_HISTORY_DAYS = 14   # need at least this much history to judge an outage
OUTAGE_ACTIVITY = 0.8   # a zero is suspicious only if the territory sold on >= 80% of recent days


def classify(value: float, window: np.ndarray):
    """Return (type, baseline_median, score), or None if the value looks normal."""
    if len(window) == 0:
        return None
    nonzero = window[window > 0]
    activity = len(nonzero) / len(window)

    if value == 0:
        if len(window) >= MIN_HISTORY_DAYS and activity >= OUTAGE_ACTIVITY:
            return "outage", float(np.median(nonzero)), round(activity, 2)
        return None

    if len(nonzero) < MIN_ACTIVE_DAYS:
        return None
    logs = np.log(nonzero)
    med = np.median(logs)
    mad = np.median(np.abs(logs - med))
    if mad == 0:
        return None
    z = 0.6745 * (np.log(value) - med) / mad
    if z > Z_THRESHOLD:
        return "spike", float(np.exp(med)), round(float(z), 2)
    if z < -Z_THRESHOLD:
        return "drop", float(np.exp(med)), round(float(z), 2)
    return None


def detect_range(start=None, end=None, verbose=True) -> list:
    """Scan stream days in [start, end] (default: everything ingested) and save the flags."""
    df = pd.read_sql(
        text("SELECT sale_date, territory_id, revenue FROM stream_daily_sales ORDER BY territory_id, sale_date"),
        app_engine,
    )
    if df.empty:
        print("Stream is empty - run the simulator first.")
        return []
    df["sale_date"] = pd.to_datetime(df["sale_date"]).dt.date
    df["revenue"] = df["revenue"].astype(float)
    start = start or df["sale_date"].min()
    end = end or df["sale_date"].max()

    flags = []
    for tid, g in df.groupby("territory_id"):
        dates = g["sale_date"].to_numpy()
        revs = g["revenue"].to_numpy()
        for i, d in enumerate(dates):
            if d < start or d > end:
                continue
            in_window = (dates >= d - timedelta(days=WINDOW_DAYS)) & (dates < d)   # past days only
            result = classify(revs[i], revs[in_window])
            if result:
                kind, baseline, score = result
                flags.append({"sale_date": d, "territory_id": int(tid), "detected_type": kind,
                              "revenue": round(float(revs[i]), 2),
                              "baseline_median": round(baseline, 2), "score": score})

    with app_engine.begin() as app:   # replace any earlier flags for this date range
        app.execute(text("DELETE FROM detected_anomalies WHERE sale_date BETWEEN :s AND :e"),
                    {"s": start, "e": end})
        if flags:
            app.execute(text("""
                INSERT INTO detected_anomalies
                    (sale_date, territory_id, detected_type, revenue, baseline_median, score)
                VALUES (:sale_date, :territory_id, :detected_type, :revenue, :baseline_median, :score)
            """), flags)

    if verbose:
        print(f"Scanned {start} -> {end}: {len(flags)} anomalies flagged")
        for f in flags:
            print(f"   {f['sale_date']}  territory {f['territory_id']:>2}  {f['detected_type']:<7} "
                  f"revenue {f['revenue']:>10}  baseline {f['baseline_median']:>10}  score {f['score']}")
    return flags


if __name__ == "__main__":
    argparse.ArgumentParser(description="Flag anomalies in the ingested stream.").parse_args()
    detect_range()
