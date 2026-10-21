"""Threshold sweep: how precision and recall trade off as the detector gets stricter.

Re-runs the detector over the whole stream for each setting and evaluates it.
The detector is causal (each day only sees its own past), so a full rescan gives
exactly the same flags as running it batch by batch while data streams in.

Usage (run from backend/):  python -m ingestion.sweep_thresholds
"""
import ingestion.detector as detector
from ingestion.detector import detect_range
from ingestion.evaluate_detection import evaluate

Z_VALUES = [3.5, 4.5, 6.0, 8.0]        # spike/drop strictness
ACTIVITY_VALUES = [0.8, 0.9, 0.95]     # outage strictness

defaults = (detector.Z_THRESHOLD, detector.OUTAGE_ACTIVITY)
print(f"{'z':>4} {'act':>5} {'flagged':>8} {'prec':>6} {'recall':>7} {'F1':>6}   spike   drop  outage")
for z in Z_VALUES:
    for act in ACTIVITY_VALUES:
        detector.Z_THRESHOLD, detector.OUTAGE_ACTIVITY = z, act
        detect_range(verbose=False)
        r = evaluate(verbose=False)
        pt = r["per_type"]
        print(f"{z:>4} {act:>5} {r['tp'] + r['fp']:>8} {r['precision']:>6.1%} {r['recall']:>7.1%} "
              f"{r['f1']:>6.3f}   {pt['spike']['recall']:>5.0%} {pt['drop']['recall']:>6.0%} {pt['outage']['recall']:>7.0%}")

# put the database back to the default settings' results
detector.Z_THRESHOLD, detector.OUTAGE_ACTIVITY = defaults
detect_range(verbose=False)
print(f"\nRestored defaults (z={defaults[0]}, activity={defaults[1]}).")
