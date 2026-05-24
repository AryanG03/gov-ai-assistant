"""
Template-Based Official Document Generator (Tool #4):
Enforces official government letter template format.
Structured output validator with JSON schema enforcement.
"""
import json
import datetime
import os
from memory.workflow_state import WorkflowState


OFFICIAL_TEMPLATE = """
================================================================================
                        GOVERNMENT OF INDIA / STATE GOVERNMENT
================================================================================

File No.: {file_no}
Date:     {date}

SUBJECT: {subject}

Sir/Madam,

{body}

{closing}

Yours faithfully,

_______________________________
{designation}
{department}
Date: {date}

================================================================================
ENCLOSURES: As above
================================================================================
"""


def generate_official_document(state: WorkflowState,
                                file_no: str = "AUTO/2024/001") -> str:
    """Generate a formatted official government document from WorkflowState."""
    date = datetime.datetime.now().strftime("%d-%B-%Y")

    # Build subject line
    authority = state.authorities[0] if state.authorities else "Competent Authority"
    subject   = (f"Compliance with Circular issued by {authority} — "
                 f"Action Taken Report")

    # Build body from draft
    body = state.draft_response if state.draft_response else (
        "This office acknowledges receipt of the circular and shall "
        "take necessary action as directed."
    )

    closing = (
        "This issues with the approval of the competent authority.\n\n"
        "A copy is forwarded to all concerned departments for information "
        "and necessary action."
    )

    doc = OFFICIAL_TEMPLATE.format(
        file_no     = file_no,
        date        = date,
        subject     = subject,
        body        = body,
        closing     = closing,
        designation = "[Designation]",
        department  = "[Department Name]",
    )
    return doc


def validate_output_schema(state: WorkflowState) -> dict:
    """
    Structured output validator:
    Enforces that the final output contains all required fields.
    """
    summary = state.to_summary_dict()
    errors  = []
    required_fields = [
        ("obligations",    list,  1),
        ("deadlines",      list,  0),
        ("authorities",    list,  1),
        ("applicability",  list,  1),
        ("draft_response", str,  50),
        ("confidence_score", float, 0),
    ]
    for field_name, expected_type, min_val in required_fields:
        val = summary.get(field_name)
        if val is None:
            errors.append(f"Missing field: {field_name}")
        elif expected_type == list and len(val) < min_val:
            errors.append(f"{field_name} must have at least {min_val} item(s)")
        elif expected_type == str and len(val) < min_val:
            errors.append(f"{field_name} too short (min {min_val} chars)")

    return {
        "valid":  len(errors) == 0,
        "errors": errors,
        "schema_enforced": True,
    }