import os
import json
from dotenv import load_dotenv
import anthropic
from agents.utils import extract_json
from agents.forecasting import get_monthly_revenue, forecast_linear

load_dotenv(dotenv_path="../.env")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DS_SYSTEM_PROMPT = """You are the Data Scientist Agent in an enterprise analytics system.
You are given the results of a DETERMINISTIC forecasting model (fit in Python with scikit-learn),
including recent historical values, the trend slope, an R-squared fit quality, and the forecast.

IMPORTANT:
- TRUST the provided numbers. Do NOT recompute or invent figures.
- Interpret the forecast for a business audience.
- Comment honestly on reliability using r_squared (low R^2 = high uncertainty / noisy or seasonal data).
- Watch for data-quality issues: if the most recent actual value is drastically lower than
  prior values, it is likely an INCOMPLETE period (partial month) and should be flagged, not
  treated as a real collapse.

Respond with ONLY a valid JSON object (no markdown) in this structure:
{
  "forecast_summary": "plain-language summary of what is predicted",
  "trend_direction": "increasing | decreasing | flat",
  "reliability": "high | medium | low, with a brief reason referencing r_squared",
  "data_quality_flags": ["any concerns, e.g. incomplete final period; empty list if none"],
  "recommendation": "one practical business recommendation based on the forecast"
}"""


def forecast_revenue(periods_ahead: int = 3) -> dict:
    """Run the deterministic forecast, then have the LLM interpret it."""
    series = get_monthly_revenue()
    model_result = forecast_linear(series, periods_ahead=periods_ahead)

    if "error" in model_result:
        return model_result

    # Show the LLM the recent history + the model output
    recent = series[-6:]
    user_content = f"""Forecasting task: project total monthly revenue {periods_ahead} months ahead.

Recent actual monthly revenue (label, value):
{json.dumps(recent, indent=2)}

Deterministic model output (trust these numbers):
{json.dumps(model_result, indent=2)}"""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=DS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    interpretation = extract_json(response.content[0].text)
    interpretation["_model"] = model_result
    interpretation["_usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return interpretation
