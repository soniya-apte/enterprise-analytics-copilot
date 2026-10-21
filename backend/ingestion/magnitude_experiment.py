"""Magnitude sensitivity: how big must an anomaly be before the detector catches it?

Every run injects anomalies at the SAME days and territories (same seed);
only their size changes. Results are saved to a CSV for the report.

Usage (run from backend/):  python -m ingestion.magnitude_experiment
"""
import contextlib
import csv
import io
import os

import ingestion.simulator as sim
from ingestion.detector import detect_range
from ingestion.evaluate_detection import evaluate

MAGNITUDES = [2, 3, 5, 10, 20]
OUT = "ingestion/results/magnitude_experiment.csv"


def replay():
    """Reset, replay the full history, and run detection (output hidden)."""
    with contextlib.redirect_stdout(io.StringIO()):
        sim.reset()
        while sim.ingest(100):
            pass
        detect_range(verbose=False)


defaults = (sim.SPIKE_RANGE, sim.DROP_RANGE)
rows = []
print(f"{'size':>5} {'prec':>6} {'recall':>7} {'F1':>6}   {'spike recall':>12} {'drop recall':>12}")
for m in MAGNITUDES:
    sim.SPIKE_RANGE = (m, m)
    sim.DROP_RANGE = (1 / m, 1 / m)
    replay()
    r = evaluate(verbose=False)
    pt = r["per_type"]
    rows.append({"magnitude": m, "precision": round(r["precision"], 4), "recall": round(r["recall"], 4),
                 "f1": round(r["f1"], 4),
                 "spike_recall": round(pt["spike"]["recall"], 4), "spike_caught": pt["spike"]["caught"],
                 "spike_injected": pt["spike"]["injected"],
                 "drop_recall": round(pt["drop"]["recall"], 4), "drop_caught": pt["drop"]["caught"],
                 "drop_injected": pt["drop"]["injected"]})
    print(f"{'x' + str(m):>5} {r['precision']:>6.1%} {r['recall']:>7.1%} {r['f1']:>6.3f}   "
          f"{pt['spike']['caught']:>4}/{pt['spike']['injected']:<3} {pt['spike']['recall']:>4.0%}  "
          f"{pt['drop']['caught']:>4}/{pt['drop']['injected']:<3} {pt['drop']['recall']:>4.0%}")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
print(f"\nSaved results to backend/{OUT}")

# Put the database back to the default anomaly sizes
sim.SPIKE_RANGE, sim.DROP_RANGE = defaults
replay()
print(f"Restored default anomalies (spike x{defaults[0]}, drop x{defaults[1]}).")
