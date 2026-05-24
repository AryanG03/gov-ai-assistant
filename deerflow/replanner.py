"""
DeerFlow 2 Equivalent — Dynamic Replanner:
Detects policy ambiguities and inserts new workflow nodes mid-execution.
"""
from deerflow.workflow_graph import WorkflowGraph, WorkflowNode
from memory.workflow_state import WorkflowState


def detect_ambiguities(state: WorkflowState) -> list[str]:
    """
    Detect conditions that require workflow replanning.
    Returns list of detected issues.
    """
    issues = []

    if len(state.pdf_text) < 200:
        issues.append("partial_document")
    if not state.obligations:
        issues.append("no_obligations_found")
    if not state.deadlines:
        issues.append("missing_deadlines")
    if state.ambiguities:
        issues.append("document_ambiguities_detected")
    if state.contradictions:
        issues.append("contradictions_detected")
    if state.confidence_score < 0.80 and state.current_iteration > 0:
        issues.append("compliance_failed")

    return issues


def replan_workflow(graph: WorkflowGraph,
                    state: WorkflowState,
                    after_node: str) -> tuple[WorkflowGraph, list[str]]:
    """
    DeerFlow 2 dynamic replanning:
    Given detected ambiguities, insert new nodes into the workflow graph.
    Returns updated graph and list of inserted node names.
    """
    ambiguities   = detect_ambiguities(state)
    inserted      = []
    insert_counter = 100  # unique node id counter

    for issue in ambiguities:
        if issue == "partial_document":
            node = WorkflowNode(
                node_id  = f"replan_{insert_counter}",
                name     = "Handle partial document",
                agent    = "analysis",
                metadata = {"triggered_by": "partial_document",
                            "action": "expand_extraction"},
            )
            graph.insert_node(node, after=after_node)
            inserted.append("Handle partial document")
            insert_counter += 1

        elif issue == "no_obligations_found":
            node = WorkflowNode(
                node_id  = f"replan_{insert_counter}",
                name     = "Deep obligation search",
                agent    = "analysis",
                metadata = {"triggered_by": "no_obligations_found",
                            "action": "broader_extraction"},
            )
            graph.insert_node(node, after=after_node)
            inserted.append("Deep obligation search")
            insert_counter += 1

        elif issue == "compliance_failed":
            node = WorkflowNode(
                node_id  = f"replan_{insert_counter}",
                name     = "Compliance-driven redraft",
                agent    = "drafting",
                metadata = {"triggered_by": "compliance_failed",
                            "action": "targeted_revision",
                            "issues": state.compliance_issues[:3]},
            )
            graph.insert_node(node, after=after_node)
            inserted.append("Compliance-driven redraft")
            insert_counter += 1

        elif issue == "document_ambiguities_detected":
            node = WorkflowNode(
                node_id  = f"replan_{insert_counter}",
                name     = "Resolve ambiguities",
                agent    = "analysis",
                metadata = {"triggered_by": "ambiguities",
                            "ambiguities": state.ambiguities},
            )
            graph.insert_node(node, after=after_node)
            inserted.append("Resolve ambiguities")
            insert_counter += 1

    state.workflow_graph = graph.to_dict()
    return graph, inserted