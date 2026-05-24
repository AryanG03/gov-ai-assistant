"""
Main Orchestrator — Government AI Multi-Agent Assistant
Combines: PraisonAI memory, DeerFlow workflow graph, Hermes self-critique
"""
import os, sys, json, datetime, argparse
from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table

from config          import OUTPUTS_DIR, COMPLIANCE_THRESHOLD
from memory.workflow_state import WorkflowState
from memory.message_bus    import MessageBus
from memory.praison_memory import PraisonMemory
from memory.audit_log      import save_audit_log
from tools.pdf_reader      import extract_text_from_pdf, get_pdf_metadata
from tools.comparator      import compare_documents
from tools.output_generator import (generate_official_document,
                                    validate_output_schema)
from agents.planner    import run_planner
from agents.analysis   import run_analysis
from agents.drafting   import run_drafting
from agents.compliance import run_compliance
from deerflow.replanner import replan_workflow

console = Console()


# ── Message bus listeners ─────────────────────────────────────────────────────

def on_plan_ready(m):
    p = m["payload"]
    console.print(f"  [cyan]► Planner:[/] {p['task_count']} tasks, "
                  f"{p['graph_nodes']} graph nodes, "
                  f"memory_used={p['memory_used']}")

def on_analysis_complete(m):
    p = m["payload"]
    console.print(f"  [green]► Analysis:[/] {p['obligations_count']} obligations, "
                  f"{p['deadlines_count']} deadlines, "
                  f"{p['ambiguities_count']} ambiguities")

def on_draft_ready(m):
    p = m["payload"]
    console.print(f"  [yellow]► Drafting:[/] {p['action']} — "
                  f"v{p['version']} ({p['length']} chars)")

def on_compliance_result(m):
    p   = m["payload"]
    clr = "green" if p["compliance_passed"] else "red"
    console.print(f"  [magenta]► Compliance:[/] "
                  f"score={p['confidence_score']:.2f} "
                  f"[{clr}]{'PASSED' if p['compliance_passed'] else 'FAILED'}[/] "
                  f"hermes_issues={len(p['hermes_critique'])}")


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_orchestrator(pdf_path: str,
                     pdf_path2: str | None = None) -> WorkflowState:
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    state   = WorkflowState(pdf_path=pdf_path, max_iterations=3)
    bus     = MessageBus()
    memory  = PraisonMemory()   # Praison AI long-term + episodic memory

    bus.subscribe("plan_ready",        on_plan_ready)
    bus.subscribe("analysis_complete", on_analysis_complete)
    bus.subscribe("draft_ready",       on_draft_ready)
    bus.subscribe("compliance_result", on_compliance_result)

    console.rule("[bold blue]Government AI Multi-Agent Assistant[/]")
    console.print(f"\n[bold]Frameworks:[/] "
                  f"PraisonAI memory · "
                  f"DeerFlow workflow graph · "
                  f"Hermes self-critique\n")

    # ── Step 1: Load PDF ──────────────────────────────────────────────────────
    console.print("[bold]Step 1:[/] Loading PDF...")
    try:
        meta = get_pdf_metadata(pdf_path)
        state.pdf_text = extract_text_from_pdf(pdf_path)
        console.print(f"  Pages: {meta['pages']} | "
                      f"Chars: {len(state.pdf_text)}")
        state.log_audit("orchestrator","pdf_loaded",
                        f"pages={meta['pages']}, chars={len(state.pdf_text)}")
    except Exception as e:
        console.print(f"  [red]PDF load error: {e}[/]")
        state.error_log.append(f"PDF load error: {e}")
        state.fallback_triggered = True
        state.pdf_text = ""

    # ── Step 1b: Multi-document comparison (optional second PDF) ─────────────
    if pdf_path2 and os.path.exists(pdf_path2):
        console.print("[bold]Step 1b:[/] Comparing with second document...")
        try:
            state.pdf_text2 = extract_text_from_pdf(pdf_path2)
            state.pdf_path2 = pdf_path2
            comp = compare_documents(
                state.pdf_text, state.pdf_text2,
                os.path.basename(pdf_path),
                os.path.basename(pdf_path2),
            )
            state.contradictions = comp.get("contradictions", [])
            state.cross_agent_memory["document_comparison"] = comp
            console.print(f"  Contradictions found: {len(state.contradictions)}")
            state.log_audit("orchestrator","comparison_complete",
                            f"contradictions={len(state.contradictions)}")
        except Exception as e:
            state.error_log.append(f"Comparison error: {e}")

    # ── Step 2: Analysis ──────────────────────────────────────────────────────
    console.print("\n[bold]Step 2:[/] Analysis Agent...")
    state = run_analysis(state, bus, memory)

    # ── Step 3: Main orchestration loop ──────────────────────────────────────
    console.print("\n[bold]Step 3:[/] Orchestration loop "
                  f"(max {state.max_iterations} iterations)...")
    graph = None

    for iteration in range(state.max_iterations):
        state.current_iteration = iteration
        console.print(f"\n  [bold]── Iteration {iteration + 1} ──[/]")

        # Planner (builds/updates DeerFlow graph)
        state, graph = run_planner(state, bus, memory)

        # DeerFlow dynamic replanning
        if iteration > 0 or state.fallback_triggered:
            graph, inserted = replan_workflow(graph, state, after_node="n5")
            if inserted:
                console.print(f"  [cyan]DeerFlow replanned:[/] "
                              f"inserted {inserted}")
                state.log_reasoning("DeerFlow",
                    f"Replanned workflow: {inserted}")

        # Drafting (multi-round negotiation on iterations > 0)
        state = run_drafting(state, bus, memory)

        # Compliance (Hermes self-critique)
        state = run_compliance(state, bus, memory)

        if state.compliance_passed:
            console.print(f"\n  [green]✓ Passed at iteration {iteration+1}[/]")
            break

        if iteration < state.max_iterations - 1:
            console.print(f"  [yellow]⚠ Failed. "
                          f"Issues: {len(state.compliance_issues)}. "
                          f"Negotiating next round...[/]")

    # ── Step 4: Store in Praison long-term memory ─────────────────────────────
    memory.store_gr_interpretation(
        pdf_path, state.obligations,
        state.deadlines, state.authorities,
    )
    console.print("\n  [cyan]Praison memory:[/] GR interpretation stored "
                  "for future runs.")

    state.workflow_complete = True
    state.cross_agent_memory["message_bus_log"] = bus.get_log()
    state.episodic_memory = memory.episodic

    return state


# ── Output generation ─────────────────────────────────────────────────────────

def generate_outputs(state: WorkflowState) -> dict:
    ts    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {}

    # 1. Human-readable draft (official template format)
    official_doc  = generate_official_document(state)
    draft_path    = os.path.join(OUTPUTS_DIR, f"draft_{ts}.txt")
    with open(draft_path,"w",encoding="utf-8") as f:
        f.write(official_doc)
    paths["draft"] = draft_path

    # 2. Structured JSON summary
    json_path = os.path.join(OUTPUTS_DIR, f"summary_{ts}.json")
    with open(json_path,"w",encoding="utf-8") as f:
        json.dump(state.to_summary_dict(), f, indent=2, ensure_ascii=False)
    paths["json_summary"] = json_path

    # 3. Compliance report
    comp_path = os.path.join(OUTPUTS_DIR, f"compliance_report_{ts}.txt")
    with open(comp_path,"w",encoding="utf-8") as f:
        f.write("COMPLIANCE REPORT\n" + "="*60 + "\n")
        f.write(f"Status:           "
                f"{'PASSED' if state.compliance_passed else 'FAILED'}\n")
        f.write(f"Confidence Score: {state.confidence_score:.2f} / 1.00\n")
        f.write(f"Threshold:        {COMPLIANCE_THRESHOLD}\n")
        f.write(f"Iterations Used:  {state.current_iteration + 1}\n")
        f.write(f"Fallback Used:    {state.fallback_triggered}\n\n")
        f.write("HERMES SELF-CRITIQUE:\n")
        for c in state.self_critique:
            f.write(f"  - {c}\n")
        f.write("\nCOMPLIANCE ISSUES:\n")
        for i in state.compliance_issues:
            f.write(f"  - {i}\n")
        f.write("\nOBLIGATIONS:\n")
        for i,o in enumerate(state.obligations,1):
            f.write(f"  {i}. {o}\n")
        f.write("\nDEADLINES:\n")
        for d in state.deadlines:
            f.write(f"  - {d}\n")
        f.write("\nAUTHORITIES:\n")
        for a in state.authorities:
            f.write(f"  - {a}\n")
        f.write("\nAMBIGUITIES DETECTED:\n")
        for a in state.ambiguities:
            f.write(f"  - {a}\n")
        f.write("\nCONTRADICTIONS (multi-doc comparison):\n")
        for c in state.contradictions:
            f.write(f"  - {c}\n")
        f.write("\nDEERFLOW WORKFLOW GRAPH:\n")
        for node in state.workflow_graph:
            f.write(f"  [{node['agent']:12}] {node['name']} "
                    f"(conditional={node['has_condition']}, "
                    f"executed={node['executed']})\n")
    paths["compliance_report"] = comp_path

    # 4. Confidence score
    conf_path = os.path.join(OUTPUTS_DIR, f"confidence_{ts}.json")
    with open(conf_path,"w",encoding="utf-8") as f:
        json.dump({
            "confidence_score":  state.confidence_score,
            "threshold":         COMPLIANCE_THRESHOLD,
            "passed":            state.compliance_passed,
            "iterations":        state.current_iteration + 1,
            "draft_version":     state.draft_version,
            "fallback_triggered":state.fallback_triggered,
            "hermes_critique_count": len(state.self_critique),
        }, f, indent=2)
    paths["confidence_score"] = conf_path

    # 5. Reasoning steps
    reason_path = os.path.join(OUTPUTS_DIR, f"reasoning_{ts}.txt")
    with open(reason_path,"w",encoding="utf-8") as f:
        f.write("REASONING STEPS\n" + "="*60 + "\n")
        for i,step in enumerate(state.reasoning_steps,1):
            f.write(f"Step {i:02d}: {step}\n")
    paths["reasoning_steps"] = reason_path

    # 6. Audit log
    audit_path = save_audit_log(
        state, state.cross_agent_memory.get("message_bus_log",[]))
    paths["audit_log"] = audit_path

    # 7. Schema validation report
    schema_result = validate_output_schema(state)
    schema_path   = os.path.join(OUTPUTS_DIR, f"schema_validation_{ts}.json")
    with open(schema_path,"w",encoding="utf-8") as f:
        json.dump(schema_result, f, indent=2)
    paths["schema_validation"] = schema_path

    return paths


# ── Display ───────────────────────────────────────────────────────────────────

def display_results(state: WorkflowState, paths: dict):
    console.print("\n")
    console.rule("[bold green]Results[/]")

    t = Table(title="Extraction Summary")
    t.add_column("Category",   style="cyan")
    t.add_column("Count",      style="magenta")
    t.add_column("Sample",     style="white")
    for label, items in [
        ("Obligations",   state.obligations),
        ("Deadlines",     state.deadlines),
        ("Authorities",   state.authorities),
        ("Applicability", state.applicability),
        ("Ambiguities",   state.ambiguities),
        ("Contradictions",state.contradictions),
    ]:
        sample = items[0][:55] if items else "-"
        t.add_row(label, str(len(items)), sample)
    console.print(t)

    color = "green" if state.compliance_passed else "red"
    console.print(Panel(
        f"[bold]Score:[/] {state.confidence_score:.2f} | "
        f"[bold]Status:[/] [{color}]"
        f"{'PASSED' if state.compliance_passed else 'FAILED'}[/]\n"
        f"[bold]Iterations:[/] {state.current_iteration+1} | "
        f"[bold]Draft v:[/] {state.draft_version} | "
        f"[bold]Fallback:[/] {state.fallback_triggered}\n"
        f"[bold]Hermes critique issues:[/] {len(state.self_critique)}\n"
        f"[bold]DeerFlow nodes:[/] {len(state.workflow_graph)}",
        title="Final Status", border_style=color,
    ))

    console.print("\n[bold]Output files:[/]")
    for name, path in paths.items():
        console.print(f"  [green]✓[/] {name}: {path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Government AI Multi-Agent Assistant")
    parser.add_argument("pdf_path", nargs="?",
        default=os.path.join("sample_docs","sample_gr.pdf"))
    parser.add_argument("--pdf2", default=None,
        help="Optional second PDF for multi-document comparison")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        console.print(f"[red]ERROR:[/] PDF not found: {args.pdf_path}")
        sys.exit(1)

    try:
        state = run_orchestrator(args.pdf_path, args.pdf2)
        paths = generate_outputs(state)
        display_results(state, paths)
        console.print("\n[bold green]✓ Complete.[/]")
    except Exception as e:
        console.print(f"\n[red]FATAL:[/] {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()