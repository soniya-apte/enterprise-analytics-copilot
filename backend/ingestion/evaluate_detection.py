"""Evaluate the streaming detector against the injected ground truth.

A detection is a true positive if it matches an injected anomaly on the same
day AND territory. Reports precision, recall, F1, recall per anomaly type, and
how many false positives fall in the known-incomplete final month.

Usage (run from backend/):  python -m ingestion.evaluate_detection
"""
from datetime import date

import pandas as pd
from sqlalchemy import text
from database import app_engine

INCOMPLETE_MONTH_START = date(2025, 6, 1)   # known data-quality issue: final month is partial


def evaluate(verbose: bool = True) -> dict:
    inj = pd.read_sql(text("SELECT sale_date, territory_id, anomaly_type FROM injected_anomalies"), app_engine)
    det = pd.read_sql(text("SELECT sale_date, territory_id, detected_type FROM detected_anomalies"), app_engine)
    m = inj.merge(det, on=["sale_date", "territory_id"], how="outer", indicator=True)

    tp = int((m["_merge"] == "both").sum())
    fp = int((m["_merge"] == "right_only").sum())
    fn = int((m["_merge"] == "left_only").sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    both = m[m["_merge"] == "both"]
    type_correct = int((both["anomaly_type"] == both["detected_type"]).sum())
    fps = m[m["_merge"] == "right_only"]
    fp_final_month = int((pd.to_datetime(fps["sale_date"]).dt.date >= INCOMPLETE_MONTH_START).sum())

    per_type = {}
    for t in ["spike", "drop", "outage"]:
        n = int((inj["anomaly_type"] == t).sum())
        caught = int((both["anomaly_type"] == t).sum())
        per_type[t] = {"injected": n, "caught": caught, "recall": caught / n if n else 0.0}

    results = {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1,
               "type_correct": type_correct, "fp_final_month": fp_final_month, "per_type": per_type}

    if verbose:
        print(f"Injected: {len(inj)} | Flagged: {len(det)}")
        print(f"TP {tp} | FP {fp} | FN {fn}")
        print(f"Precision {precision:.1%} | Recall {recall:.1%} | F1 {f1:.3f}")
        print(f"Correct type among true positives: {type_correct}/{tp}")
        print(f"False positives in the incomplete final month (Jun 2025): {fp_final_month}")
        print("Recall by injected type:")
        for t, v in per_type.items():
            print(f"   {t:<7} {v['caught']:>3}/{v['injected']:<3} = {v['recall']:.1%}")
    return results


if __name__ == "__main__":
    evaluate()
