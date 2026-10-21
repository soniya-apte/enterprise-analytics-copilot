import os
from dotenv import load_dotenv
import anthropic
from agents.utils import extract_json
from agents.schema_context import SCHEMA_CONTEXT

load_dotenv(dotenv_path="../.env")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DATA_AGENT_SYSTEM_PROMPT = f"""You are the Data Agent in an enterprise analytics system.
Your job is to translate a business question into a single, correct PostgreSQL query.

You have access to this database schema:
{SCHEMA_CONTEXT}

RULES:
- Generate ONE PostgreSQL SELECT query that answers the question.
- Use only tables/columns from the schema above.
- Always schema-qualify tables (e.g. sales.salesorderheader).
- Never use INSERT, UPDATE, DELETE, DROP, or any write operation. SELECT only.
- Prefer clear, readable SQL with explicit JOINs.
- If aggregating money, round to 2 decimals.
- The data is HISTORICAL and ends in June 2025. NEVER filter dates relative to CURRENT_DATE or NOW().
- For "recent", "last N months" or "latest" questions, anchor dates to the latest data:
  (SELECT MAX(orderdate) FROM sales.salesorderheader).
- For forecasting / "next N months" questions, return the HISTORICAL monthly series
  (all months, ordered by month). A separate forecasting model predicts the future from it.

Respond with ONLY a valid JSON object (no markdown) in this structure:
{{
  "sql": "the PostgreSQL query as a single string",
  "explanation": "one sentence explaining what the query does",
  "tables_used": ["schema.table", "..."]
}}"""


def generate_sql(question: str) -> dict:
    """Take a business question and return a SQL query (not yet executed)."""
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=DATA_AGENT_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Business question: {question}"}
        ],
    )

    result = extract_json(response.content[0].text)
    result["_usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return result
