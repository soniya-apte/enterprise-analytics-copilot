"""
Deterministic forecasting for the Data Scientist Agent.
Fits a linear trend to historical monthly data (scikit-learn) and
projects forward. The LLM later interprets these numbers, but never
computes them.
"""
import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy import text
from database import aw_engine


def get_monthly_revenue() -> list:
    """Query total revenue per month from the AdventureWorks database."""
    query = text("""
        SELECT
            DATE_TRUNC('month', orderdate) AS month,
            ROUND(SUM(totaldue)::numeric, 2) AS revenue
        FROM sales.salesorderheader
        GROUP BY month
        ORDER BY month;
    """)
    with aw_engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    # Return as list of (month_str, revenue_float)
    return [(r[0].strftime("%Y-%m"), float(r[1])) for r in rows]


def forecast_linear(series: list, periods_ahead: int = 3) -> dict:
    """
    Fit a linear trend to a time series and forecast future periods.
    `series` is a list of (label, value). Returns history, forecast, and fit quality.
    """
    if len(series) < 3:
        return {"error": "Not enough data points to forecast (need >= 3)."}

    values = np.array([v for _, v in series], dtype=float)
    X = np.arange(len(values)).reshape(-1, 1)  # 0,1,2,... as time index
    y = values

    model = LinearRegression()
    model.fit(X, y)

    # R^2: how well the trend line fits (1.0 = perfect, 0 = no linear fit)
    r_squared = round(float(model.score(X, y)), 4)

    # Forecast future indices
    future_X = np.arange(len(values), len(values) + periods_ahead).reshape(-1, 1)
    future_preds = model.predict(future_X)

    forecast = [round(float(p), 2) for p in future_preds]

    return {
        "history_points": len(series),
        "last_actual": round(float(values[-1]), 2),
        "trend_slope_per_period": round(float(model.coef_[0]), 2),
        "r_squared": r_squared,
        "forecast": forecast,
        "periods_ahead": periods_ahead,
    }
