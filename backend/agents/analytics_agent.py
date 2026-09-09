import os
import json
from dotenv import load_dotenv
import anthropic
from agents.utils import extract_json
from agents.stats import compute_stats

load_dotenv(dotenv_path="../.env")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

ANALYTICS_SYSTEM_PROMPT = """You are the Analytics Agent in an enterprise analytics system.
You are given a business question, the raw query results, and PRECISE pre-computed statistics.

IMPORTANT:
- The statistics were computed deterministically in Python. TRUST THEM for any numbers.
- Do NOT recompute or invent numbers. Cite the provided stats.
- Your job is INTERPRETATION: what do these numbers mean for the business?
- Be careful about context: e.g., a 'first-to-last change' only means a trend if the
  data is time-ordered. For a ranked list, it's not a real trend.

Respond with ONLY a valid JSON object (no markdown) in this structure:
{
  "key_findings": ["2-4 concise, specific findings grounded in the stats"],
  "notable_observations": ["patterns, outliers, or concentration worth flagging"],
  "caveats": ["any limitations, e.g. partial-period data, ranked-not-time-series"],
  "confidence": "high | medium | low — how well the data answers the question"
}"""


def analyze(question: str, columns: list, rows: list) -> dict:
    """Compute stats, then have the LLM interpret them into business insights."""
    stats = compute_stats(columns, rows)

    user_content = f"""Business question: {question}

Raw data (first rows):
columns: {columns}
rows: {rows[:20]}

Pre-computed statistics (trust these numbers):
{json.dumps(stats, indent=2)}"""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=ANALYTICS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    insights = extract_json(response.content[0].text)
    insights["_stats"] = stats
    insights["_usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return insights
