"""
Drafting Agent:
- Generates formal government response
- Uses few-shot policy adaptation
- On refinement: addresses compliance issues (negotiation)
"""
from openai import OpenAI
from memory.workflow_state import WorkflowState
from memory.message_bus import MessageBus
from memory.praison_memory import PraisonMemory
from config import (LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY,
                    GENERAL_MODEL, MAX_TOKENS, TEMPERATURE)

client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)

FEW_SHOT_EXAMPLE = """Example official response:
Subject: Compliance with Circular No. FIN/2024/001

Sir/Madam,
With reference to the above circular, this office hereby confirms compliance.
Pursuant to the directives issued, we shall submit monthly utilization
certificates by the 5th of each month. Separate accounts for scheme funds
have been established in accordance with the requirements.
Yours faithfully, [Designation]"""


def _call_llm(messages: list, max_tokens: int = 600) -> str:
    """Safe LLM call. Always returns a string."""
    try:
        response = client.chat.completions.create(
            model=GENERAL_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=TEMPERATURE,
        )
        if not response or not response.choices or len(response.choices) == 0:
            return ""
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        print(f"  [WARNING] Drafting LLM call failed: {e}")
        return ""


def run_drafting(state: WorkflowState, bus: MessageBus,
                 memory: PraisonMemory) -> WorkflowState:

    state.log_audit("drafting", "started",
                    f"iteration={state.current_iteration}")

    # Few-shot adaptation
    text_lower   = state.pdf_text.lower()
    example_type = "finance" if "finance" in text_lower else "general"
    state.log_reasoning("Drafting",
                        f"Few-shot adaptation: '{example_type}' template selected.")
    memory.add_episode("drafting", "few_shot_selected", example_type)

    # Build prompt
    if state.current_iteration == 0 or not state.draft_response:
        prompt = _initial_prompt(state)
        action = "initial draft"
        state.log_reasoning("Drafting", "Creating initial draft.")
    else:
        prompt = _negotiation_prompt(state)
        action = f"negotiation revision v{state.draft_version + 1}"
        state.log_reasoning("Drafting",
            f"Negotiation round {state.current_iteration}: "
            f"addressing {len(state.compliance_issues)} issues.")

    system = (
        "You are a senior government officer writing an official letter.\n"
        "Use formal language. Always include: Subject line, Sir/Madam, "
        "body paragraphs, Yours faithfully.\n"
        "Use phrases: pursuant to, hereby, in accordance with.\n\n"
        f"{FEW_SHOT_EXAMPLE}"
    )

    draft = _call_llm([
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ], max_tokens=600)

    # Fallback draft if LLM returns empty
    if not draft:
        state.log_reasoning("Drafting",
                            "LLM returned empty draft. Using structured fallback.")
        draft = _build_fallback_draft(state)

    state.draft_response = draft
    state.draft_version += 1
    state.draft_history.append({
        "version":   state.draft_version,
        "iteration": state.current_iteration,
        "action":    action,
        "length":    len(draft),
    })

    memory.remember("last_draft_style", {
        "tone":    "formal",
        "version": state.draft_version,
        "length":  len(draft),
    })
    memory.add_episode("drafting", action, f"length={len(draft)}")
    state.cross_agent_memory["draft_history"] = state.draft_history

    state.log_reasoning("Drafting",
        f"Draft v{state.draft_version} created ({len(draft)} chars).")
    bus.publish("draft_ready", "drafting", {
        "version":   state.draft_version,
        "iteration": state.current_iteration,
        "length":    len(draft),
        "action":    action,
    })
    state.log_audit("drafting", "complete",
                    f"version={state.draft_version}, length={len(draft)}")
    return state


def _initial_prompt(state: WorkflowState) -> str:
    obs  = "; ".join(state.obligations[:5])  or "Not clearly specified"
    dls  = "; ".join(state.deadlines[:3])    or "Not specified"
    auth = "; ".join(state.authorities[:3])  or "Not specified"

    return (
        f"Draft an official government response letter.\n\n"
        f"Obligations: {obs}\n"
        f"Deadlines: {dls}\n"
        f"Authorities: {auth}\n\n"
        f"Write the complete official letter now."
    )


def _negotiation_prompt(state: WorkflowState) -> str:
    issues = "; ".join(state.compliance_issues[:3])
    return (
        f"Revise this draft to fix these compliance issues:\n"
        f"ISSUES: {issues}\n\n"
        f"CURRENT DRAFT:\n{state.draft_response[:800]}\n\n"
        f"Write the improved draft now."
    )


def _build_fallback_draft(state: WorkflowState) -> str:
    """Structured fallback when LLM returns empty."""
    import datetime
    date    = datetime.datetime.now().strftime("%d-%B-%Y")
    obs     = "\n".join(f"  {i+1}. {o}"
                        for i, o in enumerate(state.obligations)) \
              or "  - As per circular directives"
    auth    = state.authorities[0] if state.authorities else "Competent Authority"
    dl      = state.deadlines[0]   if state.deadlines   else "As specified in circular"

    return f"""Subject: Compliance with Government Circular — Action Taken Report

Sir/Madam,

With reference to the circular issued by {auth}, this office hereby
acknowledges receipt and confirms compliance with all directives.

Pursuant to the directives contained therein, the following obligations
have been noted and action initiated:

{obs}

It is hereby intimated that compliance shall be ensured by {dl}.
The concerned departments have been duly instructed in accordance with
the requirements of the said circular.

This issues with the approval of the competent authority.

Yours faithfully,

[Designation]
[Department]
Date: {date}"""