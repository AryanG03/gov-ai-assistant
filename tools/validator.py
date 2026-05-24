"""
Compliance Validation Engine (Mandatory Tool #2):
Rule-based + JSON schema validation of WorkflowState.
"""
import json
import jsonschema
from memory.workflow_state import WorkflowState

ANALYSIS_SCHEMA = {
    "type": "object",
    "required": ["obligations","deadlines","authorities",
                 "applicability","draft_response"],
    "properties": {
        "obligations":    {"type": "array", "minItems": 1},
        "deadlines":      {"type": "array"},
        "authorities":    {"type": "array", "minItems": 1},
        "applicability":  {"type": "array", "minItems": 1},
        "draft_response": {"type": "string", "minLength": 50},
    }
}

FORMAL_PHRASES = [
    "pursuant to","in accordance with","hereby","government of",
    "it is directed","undersigned","reference","vide","enclosed herewith",
]

COMPLIANCE_RULES = [
    ("has_reference_number",
     lambda s: any(kw in s.pdf_text.lower()
                   for kw in ["no.","ref","circular","order no","g.r."]),
     0.10),
    ("has_effective_date",
     lambda s: bool(s.deadlines) or any(
         c.isdigit() for c in s.pdf_text[:500]),
     0.20),
    ("draft_is_formal",
     lambda s: sum(1 for p in FORMAL_PHRASES
                   if p in s.draft_response.lower()) >= 2,
     0.25),
    ("draft_addresses_obligations",
     lambda s: bool(s.obligations) and sum(
         1 for ob in s.obligations
         if any(w in s.draft_response.lower()
                for w in ob.lower().split()[:3])
     ) >= max(1, len(s.obligations) // 2),
     0.30),
    ("authorities_identified",
     lambda s: len(s.authorities) > 0,
     0.15),
]


def validate_schema(state: WorkflowState) -> list[str]:
    try:
        jsonschema.validate(instance=state.to_summary_dict(),
                            schema=ANALYSIS_SCHEMA)
        return []
    except jsonschema.ValidationError as e:
        return [f"Schema error: {e.message}"]


def validate_rules(state: WorkflowState) -> tuple[float, list[str], list[str]]:
    passed, failed, score = [], [], 0.0
    for name, fn, weight in COMPLIANCE_RULES:
        try:
            if fn(state):
                passed.append(name)
                score += weight
            else:
                failed.append(name)
        except Exception as e:
            failed.append(f"{name}(error:{e})")
    return round(score, 4), passed, failed


def run_full_validation(state: WorkflowState) -> dict:
    schema_errors          = validate_schema(state)
    score, passed, failed  = validate_rules(state)
    issues = schema_errors + [f"Rule failed: {r}" for r in failed]
    return {
        "confidence_score":  score,
        "schema_valid":      not schema_errors,
        "passed_rules":      passed,
        "failed_rules":      failed,
        "issues":            issues,
        "compliance_passed": score >= 0.80 and not schema_errors,
    }