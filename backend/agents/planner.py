import os
from dotenv import load_dotenv
import anthropic
from agents.utils import extract_json

load_dotenv(dotenv_path="../.env")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

PLANNER_SYSTEM_PROMPT = """You are the Planner Agent in an enterprise analytics system.
Your job is to take a business question and break it into a clear, ordered analysis plan.

You must respond with ONLY a valid JSON object (no markdown, no extra text) in this exact structure:
{
  "question_intent": "a one-sentence restatement of what the user really wants to know",
  "analysis_type": "one of: descriptive, diagnostic, predictive, comparative",
  "steps": [
    {"step": 1, "action": "short description of what to do", "rationale": "why this step is needed"}
  ],
  "data_needed": ["list", "of", "data/tables likely required"]
}

Keep plans focused: 3-6 steps. Be specific and practical."""


def create_plan(question: str) -> dict:
    """Take a business question and return a structured analysis plan."""
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=PLANNER_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Business question: {question}"}
        ],
    )

    plan = extract_json(response.content[0].text)

    plan["_usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return plan
