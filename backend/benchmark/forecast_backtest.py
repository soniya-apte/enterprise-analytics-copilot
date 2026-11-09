"""Rolling-origin backtest of the revenue forecaster (MAE, RMSE, MAPE). Free: no LLM calls.

At each origin t the models see only months [0, t) and forecast t, t+1, t+2.
Only complete months are used (the first and last months of the data are partial).
All models are scored on exactly the same target months.

Usage (run from backend/):  python -m benchmark.forecast_backtest
"""
import csv
import os

import numpy as np

from agents.forecasting import forecast_linear, get_monthly_revenue

MIN_TRAIN = 12          # first origin: 12 months of history (also enables seasonal naive)
HORIZONS = (1, 2, 3)
OUT = "benchmark/results/forecast_backtest.csv"


def linear(hist, h):
    return forecast_linear([("", v) for v in hist], periods_ahead=h)["forecast"][h - 1]


MODELS = {
    "Linear trend (deployed model)": linear,
    "Naive (last month)": lambda hist, h: hist[-1],
    "Moving average (3 months)": lambda hist, h: float(np.mean(hist[-3:])),
    "Seasonal naive (same month last year)": lambda hist, h: hist[len(hist) + h - 1 - 12],
}


def metrics(actual, pred):
    a, p = np.array(actual), np.array(pred)
    err = p - a
    return {"MAE": np.mean(np.abs(err)), "RMSE": np.sqrt(np.mean(err ** 2)),
            "MAPE": 100 * np.mean(np.abs(err) / a), "n": len(a)}


if __name__ == "__main__":
    series = get_monthly_revenue()
    complete = series[1:-1]                     # drop partial first and last months
    labels = [m for m, _ in complete]
    values = [v for _, v in complete]
    print(f"Complete months: {labels[0]} to {labels[-1]} ({len(values)} months)")

    rows = []
    for h in HORIZONS:
        origins = range(MIN_TRAIN, len(values) - h + 1)
        actual = [values[t + h - 1] for t in origins]
        print(f"\nHorizon {h} month(s) ahead - {len(actual)} forecasts, targets "
              f"{labels[MIN_TRAIN + h - 1]} to {labels[-1]}")
        print(f"   {'model':<40}{'MAE ($K)':>10}{'RMSE ($K)':>11}{'MAPE':>8}")
        for name, fn in MODELS.items():
            pred = [fn(values[:t], h) for t in origins]
            m = metrics(actual, pred)
            rows.append({"horizon": h, "model": name, "mae": round(m["MAE"], 2),
                         "rmse": round(m["RMSE"], 2), "mape": round(m["MAPE"], 2), "n": m["n"]})
            print(f"   {name:<40}{m['MAE'] / 1e3:>10,.0f}{m['RMSE'] / 1e3:>11,.0f}{m['MAPE']:>7.1f}%")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"\nSaved to backend/{OUT}")
