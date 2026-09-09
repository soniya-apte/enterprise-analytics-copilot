import json
import re


def extract_json(raw_text: str) -> dict:
    """
    Robustly extract a JSON object from an LLM response.
    Handles markdown code fences, leading/trailing text, and whitespace.
    """
    text = raw_text.strip()

    # Remove markdown code fences if present (```json ... ``` or ``` ... ```)
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
        text = text.strip()

    # As a fallback, extract the outermost {...} block
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

    return json.loads(text)
