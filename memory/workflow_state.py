"""
WorkflowState: single shared object passed through every agent.
This is the cross-agent memory backbone (Praison AI memory concept).
"""
from dataclasses import dataclass, field
from typing import Any
import datetime


@dataclass
class WorkflowState:
    # Input
    pdf_path: str  = ""
    pdf_path2: str = ""          # second document for comparison
    pdf_text: str  = ""
    pdf_text2: str = ""
    pdf_chunks: list[str] = field(default_factory=list)

    # Planner
    task_plan: list[dict]     = field(default_factory=list)
    workflow_graph: list[dict] = field(default_factory=list)  # DeerFlow graph nodes

    # Analysis
    obligations:   list[str] = field(default_factory=list)
    deadlines:     list[str] = field(default_factory=list)
    authorities:   list[str] = field(default_factory=list)
    applicability: list[str] = field(default_factory=list)
    ambiguities:   list[str] = field(default_factory=list)   # robustness
    contradictions: list[str] = field(default_factory=list)  # comparator tool

    # Drafting
    draft_response: str = ""
    draft_version:  int = 0
    draft_history:  list[dict] = field(default_factory=list)

    # Compliance
    compliance_issues:  list[str] = field(default_factory=list)
    compliance_passed:  bool      = False
    confidence_score:   float     = 0.0
    self_critique:      list[str] = field(default_factory=list)
    reasoning_steps:    list[str] = field(default_factory=list)

    # Orchestration
    current_iteration: int  = 0
    max_iterations:    int  = 3
    workflow_complete: bool = False
    error_log:         list[str] = field(default_factory=list)
    fallback_triggered: bool = False

    # Audit
    audit_trail: list[dict] = field(default_factory=list)

    # Cross-agent memory (Praison AI episodic memory)
    cross_agent_memory: dict[str, Any] = field(default_factory=dict)
    episodic_memory:    list[dict]     = field(default_factory=list)

    def log_audit(self, agent: str, action: str, detail: str = ""):
        self.audit_trail.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "agent":     agent,
            "action":    action,
            "detail":    detail,
            "iteration": self.current_iteration,
        })

    def log_reasoning(self, agent: str, step: str):
        self.reasoning_steps.append(f"[{agent}] {step}")

    def to_summary_dict(self) -> dict:
        return {
            "pdf_path":          self.pdf_path,
            "obligations":       self.obligations,
            "deadlines":         self.deadlines,
            "authorities":       self.authorities,
            "applicability":     self.applicability,
            "ambiguities":       self.ambiguities,
            "contradictions":    self.contradictions,
            "draft_response":    self.draft_response,
            "draft_version":     self.draft_version,
            "compliance_passed": self.compliance_passed,
            "compliance_issues": self.compliance_issues,
            "confidence_score":  self.confidence_score,
            "self_critique":     self.self_critique,
            "reasoning_steps":   self.reasoning_steps,
            "iterations_taken":  self.current_iteration + 1,
            "task_plan":         self.task_plan,
            "fallback_triggered":self.fallback_triggered,
        }