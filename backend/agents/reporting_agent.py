import os
import json
from dotenv import load_dotenv
import anthropic
from agents.utils import extract_json

load_dotenv(dotenv_path="../.env")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

REPORTING_SYSTEM_PROMPT = """You are the Reporting Agent in an enterprise analytics system.
You receive the structured outputs of prior agents (the question, the data retrieved,
analytics insights, and any data-science results). Your job is to synthesize them into a
clear, executive-ready report. You do NOT compute new numbers — only use what is provided.

Guidelines:
- Write for a busy executive: clear, concise, jargon-light.
- Ground every claim in the provided data/insights. Do not invent figures.
- Preserve any caveats or confidence limitations from upstream agents — be honest.
- For charts, produce SPECIFICATIONS (what to plot), not drawings. The frontend renders them.

Respond with ONLY a valid JSON object (no markdown) in this structure:
{
  "executive_summary": "2-4 sentence narrative answering the question",
  "key_takeaways": ["3-5 concise bullet points"],
  "recommendations": ["2-4 actionable recommendations"],
  "chart_specs": [
    {
      "type": "bar | line | pie",
      "title": "chart title",
      "x_label": "what the x-axis represents",
      "y_label": "what the y-axis represents",
      "data_description": "which data from the inputs should populate this chart"
    }
  ],
  "confidence_note": "honest one-sentence statement of overall reliability"
}"""


def generate_report(question: str, context: dict) -> dict:
    """
    Synthesize prior agent outputs into an executive report.
    `context` is a dict that may contain: data (columns/rows), analytics insights,
    forecast results, anomaly results, driver analysis — whatever is available.
    """
    user_content = f"""Business question: {question}

Here are the structured results from the analysis pipeline:
{json.dumps(context, indent=2, default=str)}

Synthesize these into an executive report."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1536,
        system=REPORTING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    report = extract_json(response.content[0].text)
    report["_usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return report
