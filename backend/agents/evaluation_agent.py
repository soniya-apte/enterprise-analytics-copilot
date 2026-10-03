import os
import json
from dotenv import load_dotenv
import anthropic
from agents.utils import extract_json

load_dotenv(dotenv_path="../.env")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

EVALUATION_SYSTEM_PROMPT = """You are the Evaluation Agent in an enterprise analytics system.
Your job is QUALITY CONTROL. You critically assess the outputs of the other agents.
You are a skeptical reviewer, NOT a cheerleader. Actively hunt for problems.

You are given: the original question, the SQL that was run, the data returned, and the
insights/report produced. Assess:

1. SQL CORRECTNESS: Does the SQL actually answer the question asked? Wrong table? Wrong
   aggregation? Missing filter? If it looks correct, say so; if not, explain the flaw.

2. GROUNDEDNESS: Is every claim in the insights/report supported by the data provided?
   Flag any statement that is invented, exaggerated, or not traceable to the data.

3. CONFIDENCE CALIBRATION: Is the stated confidence appropriate? Penalize overconfidence
   when data is limited, partial, or a snapshot. Reward honest caveats.

Be specific. Cite concrete issues. If something is genuinely good, acknowledge it briefly.

Respond with ONLY a valid JSON object (no markdown) in this structure:
{
  "sql_assessment": {"verdict": "correct | questionable | incorrect", "reason": "..."},
  "groundedness": {"verdict": "grounded | partially_grounded | ungrounded", "issues": ["specific ungrounded claims, or empty list"]},
  "confidence_calibration": {"verdict": "well_calibrated | overconfident | underconfident", "reason": "..."},
  "overall_score": "a number 0-100 reflecting overall answer quality",
  "summary": "one-sentence overall judgment"
}"""


def evaluate(question: str, sql: str, columns: list, rows: list, report: dict) -> dict:
    """Critically evaluate the pipeline's output for a given question."""
    user_content = f"""Original question: {question}

SQL that was executed:
{sql}

Data returned (columns + up to 20 rows):
columns: {columns}
rows: {rows[:20]}

Report / insights produced:
{json.dumps(report, indent=2, default=str)}

Critically evaluate this analysis."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=EVALUATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    evaluation = extract_json(response.content[0].text)
    evaluation["_usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return evaluation
