"""
Analysis Agent:
- Chunks PDF, analyzes each chunk
- Detects ambiguities (robustness)
- Stores to Praison episodic memory
- Publishes to MessageBus
"""
from memory.workflow_state import WorkflowState
from memory.message_bus import MessageBus
from memory.praison_memory import PraisonMemory
from tools.chunker import smart_chunk_text
from tools.gr_analyzer import analyze_chunk, merge_analyses


def run_analysis(state: WorkflowState, bus: MessageBus,
                 memory: PraisonMemory) -> WorkflowState:

    state.log_audit("analysis", "started", f"chars={len(state.pdf_text)}")
    state.log_reasoning("Analysis",
                        f"PDF length: {len(state.pdf_text)} chars.")

    # ── Robustness: handle partial/empty document ─────────────────────────────
    if len(state.pdf_text.strip()) < 100:
        state.fallback_triggered = True
        state.ambiguities.append("Document is too short or incomplete.")
        state.log_reasoning("Analysis",
                            "WARNING: Partial document detected. Fallback activated.")
        state.log_audit("analysis", "fallback", "partial document")
        memory.add_episode("analysis", "fallback", "partial_document")
        state.obligations   = ["[Unclear — document appears incomplete]"]
        state.authorities   = ["[Not specified]"]
        state.applicability = ["[Not specified]"]
        bus.publish("analysis_complete", "analysis", {
            "obligations_count": 0,
            "deadlines_count": 0,
            "authorities_count": 0,
            "ambiguities_count": 1,
            "fallback": True,
        })
        return state

    # ── Chunk and analyze ─────────────────────────────────────────────────────
    chunks = smart_chunk_text(state.pdf_text)
    state.pdf_chunks = chunks
    state.log_reasoning("Analysis", f"Split into {len(chunks)} chunk(s).")

    analyses = []
    for i, chunk in enumerate(chunks):
        state.log_reasoning("Analysis",
                            f"Processing chunk {i+1}/{len(chunks)}...")
        result = analyze_chunk(chunk, i, len(chunks))
        analyses.append(result)
        state.log_audit("analysis", f"chunk_{i+1}",
                        f"obligations={len(result['obligations'])}")

    merged = merge_analyses(analyses)

    # ── Merge into state ──────────────────────────────────────────────────────
    if state.current_iteration == 0:
        state.obligations   = merged["obligations"]
        state.deadlines     = merged["deadlines"]
        state.authorities   = merged["authorities"]
        state.applicability = merged["applicability"]
        state.ambiguities   = merged["ambiguities"]
    else:
        for key in ["obligations", "deadlines", "authorities",
                    "applicability", "ambiguities"]:
            existing  = set(getattr(state, key))
            new_items = [x for x in merged[key] if x not in existing]
            getattr(state, key).extend(new_items)

    # ── Robustness: flag if nothing extracted ─────────────────────────────────
    if not state.obligations:
        state.fallback_triggered = True
        state.ambiguities.append(
            "No obligations found. Document may be ambiguous or non-standard.")
        state.log_reasoning("Analysis",
                            "No obligations extracted. Flagging as ambiguous.")

    state.log_reasoning("Analysis",
        f"Found {len(state.obligations)} obligations, "
        f"{len(state.deadlines)} deadlines, "
        f"{len(state.authorities)} authorities, "
        f"{len(state.ambiguities)} ambiguities.")

    # ── Store in Praison episodic memory ──────────────────────────────────────
    memory.add_episode("analysis", "extraction_complete",
        f"obligations={len(state.obligations)}, "
        f"ambiguities={len(state.ambiguities)}")
    state.cross_agent_memory["analysis_summary"] = {
        "obligations_count": len(state.obligations),
        "sample_obligation": state.obligations[0] if state.obligations else "",
        "ambiguities_count": len(state.ambiguities),
    }

    # ── Publish ───────────────────────────────────────────────────────────────
    bus.publish("analysis_complete", "analysis", {
        "obligations_count":  len(state.obligations),
        "deadlines_count":    len(state.deadlines),
        "authorities_count":  len(state.authorities),
        "ambiguities_count":  len(state.ambiguities),
    })
    state.log_audit("analysis", "complete",
                    f"obligations={len(state.obligations)}")
    return state