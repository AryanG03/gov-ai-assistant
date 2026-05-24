"""
GR Analyzer Tool - creates fresh client per call to avoid connection issues.
"""
import re
from openai import OpenAI
from config import (LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY,
                    GENERAL_MODEL, TEMPERATURE)


def _get_client():
    """Create a fresh OpenAI client each time."""
    return OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)


def _clean_text(text: str) -> str:
    """Remove page markers and clean whitespace."""
    text = re.sub(r'\[PAGE \d+\]\n?', '', text)
    return text.strip()


def _ask(question: str, text: str) -> str:
    """
    Ask a single direct question about the text.
    Returns raw string response or empty string.
    """
    client = _get_client()
    prompt = f"{question}\n\nTEXT:\n{text[:800]}"
    try:
        response = client.chat.completions.create(
            model=GENERAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
        )
        if (response
                and response.choices
                and len(response.choices) > 0
                and response.choices[0].message.content):
            return response.choices[0].message.content.strip()
        return ""
    except Exception as e:
        print(f"  [WARNING] LLM call failed: {e}")
        return ""


def _parse_list(raw: str) -> list[str]:
    """Parse bullet list into clean Python list."""
    items = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("- "):
            line = line[2:].strip()
        elif line.startswith("* "):
            line = line[2:].strip()
        elif line and line[0].isdigit() and "." in line:
            line = line.split(".", 1)[-1].strip()
        if line and len(line) > 3 and "none" not in line.lower():
            items.append(line)
    return items


def analyze_chunk(chunk: str, idx: int, total: int) -> dict:
    """Extract all fields from one chunk using 4 direct LLM calls."""
    chunk = _clean_text(chunk)
   

    raw_obs  = _ask(
        "What are the obligations or directives in this text? "
        "List each one starting with -. If none, write: - None.",
        chunk)
    

    raw_dl   = _ask(
        "What deadlines or dates are mentioned in this text? "
        "List each one starting with -. If none, write: - None.",
        chunk)
    

    raw_auth = _ask(
        "What authorities or departments are mentioned in this text? "
        "List each one starting with -. If none, write: - None.",
        chunk)
    

    raw_appl = _ask(
        "Who does this circular apply to? "
        "List each one starting with -. If none, write: - None.",
        chunk)


    return {
        "obligations":   _parse_list(raw_obs),
        "deadlines":     _parse_list(raw_dl),
        "authorities":   _parse_list(raw_auth),
        "applicability": _parse_list(raw_appl),
        "ambiguities":   [],
    }


def merge_analyses(analyses: list[dict]) -> dict:
    merged = {k: [] for k in
              ["obligations", "deadlines", "authorities",
               "applicability", "ambiguities"]}
    seen = {k: set() for k in merged}
    for a in analyses:
        for key in merged:
            for item in a.get(key, []):
                if item not in seen[key]:
                    seen[key].add(item)
                    merged[key].append(item)
    return merged