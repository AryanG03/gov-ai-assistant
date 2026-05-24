"""
Multi-Document Comparison Tool (Tool #3 — bonus):
Detects contradictions or superseding clauses between two circulars.
"""
from openai import OpenAI
from config import (LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY,
                    GENERAL_MODEL, MAX_TOKENS, TEMPERATURE)

client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)


def compare_documents(text1: str, text2: str,
                      label1: str = "Document 1",
                      label2: str = "Document 2") -> dict:
    """
    Compare two government documents and find contradictions,
    superseding clauses, or complementary directives.
    """
    prompt = f"""Compare these two government documents and identify:

{label1} (first 800 chars):
{text1[:800]}

{label2} (first 800 chars):
{text2[:800]}

List findings in this format:

CONTRADICTIONS:
- [any directly conflicting directives]

SUPERSEDING:
- [which document overrides the other and on what point]

COMPLEMENTARY:
- [directives that align or reinforce each other]

RECOMMENDATION:
- [which document takes precedence and why]"""

    response = client.chat.completions.create(
        model=GENERAL_MODEL,
        messages=[
            {"role": "system", "content": "You are a senior legal analyst specializing in government policy documents."},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    raw = response.choices[0].message.content or ""
    return _parse_comparison(raw)


def _parse_comparison(raw: str) -> dict:
    result = {
        "contradictions": [],
        "superseding":    [],
        "complementary":  [],
        "recommendation": [],
        "raw":            raw,
    }
    key_map = {
        "CONTRADICTIONS:": "contradictions",
        "SUPERSEDING:":    "superseding",
        "COMPLEMENTARY:":  "complementary",
        "RECOMMENDATION:": "recommendation",
    }
    current = None
    for line in raw.splitlines():
        line = line.strip()
        if line in key_map:
            current = key_map[line]
        elif current and line.startswith("- "):
            item = line[2:].strip()
            if item:
                result[current].append(item)
    return result