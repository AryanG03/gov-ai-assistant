"""
Planner Agent:
- Uses LLM to decompose the request into subtasks
- Builds the DeerFlow workflow graph
- Checks Praison memory for past similar documents
- Publishes plan to MessageBus
"""
from openai import OpenAI
from memory.workflow_state import WorkflowState
from memory.message_bus import MessageBus
from memory.praison_memory import PraisonMemory
from deerflow.workflow_graph import WorkflowGraph, WorkflowNode
from config import (LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY,
                    PLANNER_MODEL, MAX_TOKENS, TEMPERATURE)
import os

client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)


def _call_llm(messages: list, max_tokens: int = 200) -> str:
    """Safe LLM call with full error handling. Always returns a string."""
    try:
        response = client.chat.completions.create(
            model=PLANNER_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=TEMPERATURE,
        )
        if not response or not response.choices or len(response.choices) == 0:
            return ""
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        print(f"  [WARNING] Planner LLM call failed: {e}")
        return ""


def run_planner(state: WorkflowState, bus: MessageBus,
                memory: PraisonMemory) -> tuple[WorkflowState, WorkflowGraph]:

    state.log_audit("planner", "started",
                    f"iteration={state.current_iteration}")
    state.log_reasoning("Planner",
                        f"Starting at iteration {state.current_iteration}.")

    # ── Check Praison long-term memory ────────────────────────────────────────
    doc_name    = os.path.basename(state.pdf_path).replace(".pdf", "")
    past        = memory.recall(doc_name)
    memory_used = past is not None
    memory_hint = ""
    if past:
        memory_hint = (f" Past obligations found: "
                       f"{past.get('obligations', [])[:2]}.")
        state.log_reasoning("Planner",
                            "Found past GR interpretation in long-term memory.")
        memory.add_episode("planner", "memory_recall",
                           f"Recalled past analysis for {doc_name}")

    # ── LLM task decomposition (short prompt to avoid empty response) ─────────
    doc_preview = state.pdf_text[:300] if state.pdf_text else "Government circular."

    raw = _call_llm([
        {"role": "system", "content":
            "You are a government workflow planner. "
            "List exactly 3 tasks needed to process this document. "
            "Number each task 1. 2. 3. One task per line. No other text."},
        {"role": "user", "content": f"Document:\n{doc_preview}\n\nList 3 tasks:"},
    ], max_tokens=150)

    tasks = _parse_tasks(raw)
    state.task_plan = tasks

    # ── Build DeerFlow workflow graph ─────────────────────────────────────────
    graph = _build_workflow_graph(state)
    state.workflow_graph = graph.to_dict()
    state.log_reasoning("Planner",
                        f"DeerFlow graph built with {len(graph.nodes)} nodes.")

    # ── Publish ───────────────────────────────────────────────────────────────
    bus.publish("plan_ready", "planner", {
        "iteration":         state.current_iteration,
        "task_count":        len(tasks),
        "graph_nodes":       len(graph.nodes),
        "memory_used":       memory_used,
        "compliance_issues": state.compliance_issues,
    })

    state.log_audit("planner", "complete",
                    f"tasks={len(tasks)}, graph_nodes={len(graph.nodes)}")
    memory.add_episode("planner", "plan_created",
                       f"{len(tasks)} tasks, iteration {state.current_iteration}")
    return state, graph


def _parse_tasks(raw: str) -> list[dict]:
    agents = ["analysis", "drafting", "compliance", "analysis", "compliance"]
    tasks  = []
    for i, line in enumerate(raw.strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        if line and line[0].isdigit():
            line = line.split(".", 1)[-1].strip()
        if line:
            tasks.append({
                "step":   i + 1,
                "agent":  agents[i] if i < len(agents) else "compliance",
                "task":   line,
                "status": "pending",
            })

    # Always ensure at least 3 tasks exist
    if not tasks:
        tasks = [
            {"step": 1, "agent": "analysis",
             "task": "Extract all obligations, deadlines, authorities",
             "status": "pending"},
            {"step": 2, "agent": "drafting",
             "task": "Draft official government response",
             "status": "pending"},
            {"step": 3, "agent": "compliance",
             "task": "Validate draft and score compliance",
             "status": "pending"},
        ]
    return tasks


def _build_workflow_graph(state: WorkflowState) -> WorkflowGraph:
    """Build the DeerFlow workflow graph with conditional nodes."""
    graph = WorkflowGraph()
    graph.add_node(WorkflowNode("n1", "Load & chunk PDF",    "orchestrator"))
    graph.add_node(WorkflowNode("n2", "Extract obligations", "analysis"),
                   after="n1")
    graph.add_node(WorkflowNode("n3", "Check ambiguities",   "analysis",
        condition=lambda s: bool(s.pdf_text)),
                   after="n2")
    graph.add_node(WorkflowNode("n4", "Draft response",      "drafting",
        condition=lambda s: bool(s.obligations or s.pdf_text)),
                   after="n3")
    graph.add_node(WorkflowNode("n5", "Compliance check",    "compliance",
        condition=lambda s: bool(s.draft_response)),
                   after="n4")
    graph.add_node(WorkflowNode("n6", "Replan if needed",    "orchestrator",
        condition=lambda s: not s.compliance_passed
                            and s.current_iteration < s.max_iterations),
                   after="n5")
    graph.add_node(WorkflowNode("n7", "Generate outputs",    "orchestrator",
        condition=lambda s: s.compliance_passed
                            or s.current_iteration >= s.max_iterations),
                   after="n6")
    return graph