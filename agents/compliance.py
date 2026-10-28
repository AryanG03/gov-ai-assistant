"""
Compliance / Critic Agent (Hermes-driven self-critique):
- Runs rule-based validation
- Uses Hermes model for meta-reasoning self-critique
- Generates counter-arguments without human feedback
"""
from openai import OpenAI
from memory.workflow_state import WorkflowState
from memory.message_bus import MessageBus
from memory.praison_memory import PraisonMemory
from tools.validator import run_full_validation
from config import (LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY, HERMES_MODEL)
import config

hermes_client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)


def _call_hermes(messages: list, max_tokens: int = 300) -> str:
    """Safe Hermes LLM call. Always returns a string."""
    try:
        response = hermes_client.chat.completions.create(
            model=HERMES_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2,
        )
        if not response or not response.choices or len(response.choices) == 0:
            return ""
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        print(f"  [WARNING] Hermes critique call failed: {e}")
        return ""


def run_compliance(state: WorkflowState, bus: MessageBus,
                   memory: PraisonMemory) -> WorkflowState:

    state.log_audit("compliance", "started",
                    f"iteration={state.current_iteration}")
    state.log_reasoning("Compliance",
        f"Running validation at iteration {state.current_iteration}.")

    # Step 1: Rule-based validation
    result = run_full_validation(state)
    state.confidence_score  = result["confidence_score"]
    state.compliance_issues = result["issues"]
    state.compliance_passed = state.confidence_score >= config.COMPLIANCE_THRESHOLD

    state.log_reasoning("Compliance",
        f"Rule-based score: {state.confidence_score:.2f}. "
        f"Passed: {result['passed_rules']}. "
        f"Failed: {result['failed_rules']}.")

    # Step 2: Hermes self-critique
    critique_issues = _hermes_self_critique(state)
    state.self_critique = critique_issues

    if critique_issues:
        for issue in critique_issues:
            tagged = f"[Hermes critique] {issue}"
            if tagged not in state.compliance_issues:
                state.compliance_issues.append(tagged)
        penalty = min(0.15, 0.03 * len(critique_issues))
        state.confidence_score  = max(0.0, state.confidence_score - penalty)
        state.compliance_passed = state.confidence_score >= COMPLIANCE_THRESHOLD

    state.log_reasoning("Compliance",
        f"After Hermes self-critique: score={state.confidence_score:.2f}, "
        f"passed={state.compliance_passed}, "
        f"critique_issues={len(critique_issues)}.")

    # Step 3: Save to Praison memory
    memory.add_episode("compliance", "validation_complete",
        f"score={state.confidence_score:.2f}, passed={state.compliance_passed}")
    memory.remember("last_compliance_result", {
        "score":  state.confidence_score,
        "passed": state.compliance_passed,
        "issues": state.compliance_issues[:5],
    })
    state.cross_agent_memory["compliance_result"] = {
        "score":     state.confidence_score,
        "passed":    state.compliance_passed,
        "iteration": state.current_iteration,
        "critique":  critique_issues,
    }

    # Step 4: Publish
    bus.publish("compliance_result", "compliance", {
        "confidence_score":  state.confidence_score,
        "compliance_passed": state.compliance_passed,
        "issues_count":      len(state.compliance_issues),
        "iteration":         state.current_iteration,
        "hermes_critique":   critique_issues,
    })

    state.log_audit("compliance", "complete",
        f"score={state.confidence_score:.2f}, passed={state.compliance_passed}")
    return state


def _hermes_self_critique(state: WorkflowState) -> list[str]:
    """
    Hermes Agent meta-reasoning self-critique.
    Generates counter-arguments against the draft without human feedback.
    """
    if not state.draft_response:
        return ["No draft available to critique."]

    obligations_text = "; ".join(state.obligations[:3]) or "None extracted"

    # Keep prompt short to avoid empty response
    prompt = (
        f"Review this government draft. Find up to 3 specific problems.\n\n"
        f"DRAFT (first 600 chars):\n{state.draft_response[:600]}\n\n"
        f"OBLIGATIONS TO ADDRESS: {obligations_text}\n\n"
        f"If draft is acceptable write: APPROVED\n"
        f"Otherwise write each problem as:\n"
        f"ISSUE: [specific problem]\n\n"
        f"Be brief and specific."
    )

    raw = _call_hermes([
        {"role": "system", "content":
            "You are a strict government compliance reviewer. "
            "Find real problems only. Be concise."},
        {"role": "user", "content": prompt},
    ], max_tokens=200)

    if not raw:
        return []

    if "APPROVED" in raw.upper() and "ISSUE:" not in raw.upper():
        return []

    issues = []
    for line in raw.splitlines():
        line = line.strip()
        if line.upper().startswith("ISSUE:"):
            issues.append(line[6:].strip())

    return issues