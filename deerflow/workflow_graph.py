"""
DeerFlow 2 Equivalent — Workflow Graph:
Implements conditional branching and visual workflow nodes.
DeerFlow 2's core concept: tasks are nodes in a directed graph.
Edges are conditional (only traverse if condition is met).
This replaces DeerFlow 2's visual flow engine with a Python implementation.
"""
from dataclasses import dataclass, field
from typing import Callable, Any
from memory.workflow_state import WorkflowState


@dataclass
class WorkflowNode:
    """A single node in the DeerFlow-style workflow graph."""
    node_id:   str
    name:      str
    agent:     str
    condition: Callable[[WorkflowState], bool] | None = None
    # condition=None means always execute
    metadata:  dict = field(default_factory=dict)

    def should_execute(self, state: WorkflowState) -> bool:
        if self.condition is None:
            return True
        return self.condition(state)


class WorkflowGraph:
    """
    DeerFlow 2 equivalent: directed graph of workflow nodes.
    Supports mid-execution replanning by inserting new nodes.
    """
    def __init__(self):
        self.nodes:  list[WorkflowNode] = []
        self.edges:  dict[str, list[str]] = {}  # node_id → [next_node_ids]
        self._executed: set[str] = set()

    def add_node(self, node: WorkflowNode, after: str | None = None):
        """Add a node to the graph, optionally after an existing node."""
        self.nodes.append(node)
        self.edges[node.node_id] = []
        if after and after in self.edges:
            self.edges[after].append(node.node_id)

    def insert_node(self, node: WorkflowNode, after: str):
        """
        DeerFlow 2 dynamic replanning:
        Insert a new node mid-execution after a specified node.
        """
        # Find what 'after' currently points to
        existing_next = list(self.edges.get(after, []))
        # Insert new node between 'after' and its current successors
        self.nodes.append(node)
        self.edges[node.node_id] = existing_next
        self.edges[after] = [node.node_id]

    def get_execution_order(self,
                            state: WorkflowState) -> list[WorkflowNode]:
        """
        Traverse the graph and return nodes that should execute
        given the current WorkflowState (conditional branching).
        """
        if not self.nodes:
            return []

        visited = []
        queue   = [self.nodes[0].node_id]
        seen    = set()

        while queue:
            nid  = queue.pop(0)
            if nid in seen:
                continue
            seen.add(nid)

            node = next((n for n in self.nodes if n.node_id == nid), None)
            if not node:
                continue

            if node.should_execute(state):
                visited.append(node)
                queue.extend(self.edges.get(nid, []))

        return visited

    def mark_executed(self, node_id: str):
        self._executed.add(node_id)

    def to_dict(self) -> list[dict]:
        """Export graph as list of dicts for audit trail."""
        return [
            {
                "node_id":   n.node_id,
                "name":      n.name,
                "agent":     n.agent,
                "has_condition": n.condition is not None,
                "executed":  n.node_id in self._executed,
            }
            for n in self.nodes
        ]