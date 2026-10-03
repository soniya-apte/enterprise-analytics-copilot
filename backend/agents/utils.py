import json
import re


def extract_json(raw_text: str) -> dict:
    """
    Robustly extract a JSON object from an LLM response.
    Handles markdown code fences, and leading/trailing text, by locating the
    first balanced {...} object in the text and parsing only that.
    """
    text = raw_text.strip()

    # Fast path: clean JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Robust path: find the first balanced {...} block by scanning braces
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in LLM response.")

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                return json.loads(candidate)

    raise ValueError("No balanced JSON object found in LLM response.")
