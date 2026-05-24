"""
Audit Log: writes the full audit trail to disk.
Satisfies: Automated audit trail generation requirement.
"""
import json
import os
import datetime
from memory.workflow_state import WorkflowState


def save_audit_log(state: WorkflowState, bus_log: list,
                   output_dir: str = "outputs") -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"audit_log_{ts}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at":     ts,
            "total_iterations": state.current_iteration + 1,
            "workflow_complete": state.workflow_complete,
            "fallback_triggered": state.fallback_triggered,
            "audit_trail":      state.audit_trail,
            "message_bus_log":  bus_log,
            "episodic_memory":  state.episodic_memory,
            "error_log":        state.error_log,
        }, f, indent=2, ensure_ascii=False)

    return path