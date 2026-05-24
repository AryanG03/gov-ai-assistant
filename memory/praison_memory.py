"""
Praison AI Cross-Agent Memory:
- Long-term memory: persists across runs (saved to disk as JSON)
- Episodic memory: remembers past GR interpretations within a session
- Agents read this before processing to avoid redundant analysis
"""
import json
import os
import datetime
from config import MEMORY_FILE


class PraisonMemory:
    """
    Implements Praison AI's long-term and episodic memory concept.
    Long-term memory persists to disk.
    Episodic memory lives in the session.
    """

    def __init__(self):
        self.long_term: dict  = self._load_long_term()
        self.episodic:  list  = []

    def _load_long_term(self) -> dict:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_long_term(self):
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.long_term, f, indent=2, ensure_ascii=False)

    def remember(self, key: str, value: dict):
        """Save something to long-term memory."""
        self.long_term[key] = {
            "value":     value,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.save_long_term()

    def recall(self, key: str) -> dict | None:
        """Retrieve from long-term memory."""
        entry = self.long_term.get(key)
        return entry["value"] if entry else None

    def add_episode(self, agent: str, action: str, result: str):
        """Add an episode to episodic memory (session only)."""
        self.episodic.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "agent":     agent,
            "action":    action,
            "result":    result,
        })

    def get_relevant_past(self, doc_keywords: list[str]) -> str:
        """
        Search long-term memory for past GR interpretations
        relevant to the current document. Returns summary string
        for injection into agent prompts.
        """
        matches = []
        for key, entry in self.long_term.items():
            for kw in doc_keywords:
                if kw.lower() in key.lower():
                    matches.append(f"Past analysis of '{key}': {json.dumps(entry['value'])[:300]}")
                    break
        if not matches:
            return "No relevant past GR interpretations found in memory."
        return "MEMORY CONTEXT:\n" + "\n".join(matches[:3])

    def store_gr_interpretation(self, doc_path: str, obligations: list,
                                deadlines: list, authorities: list):
        """Store a completed GR interpretation for future reference."""
        key = os.path.basename(doc_path).replace(".pdf", "")
        self.remember(key, {
            "obligations":  obligations,
            "deadlines":    deadlines,
            "authorities":  authorities,
            "doc_path":     doc_path,
        })