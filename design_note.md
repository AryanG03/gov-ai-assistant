# Design Note — Government AI Multi-Agent Assistant

## Model Selection Rationale

**Nous-Hermes-2-Mistral-7B-DPO** was selected as the primary model
for all agents for three reasons:

1. It is fine-tuned specifically for instruction following and
   structured output generation, which is critical for extracting
   obligations in a consistent parseable format.

2. The "Hermes" fine-tune includes meta-reasoning capabilities —
   the model can reason about its own outputs and generate
   counter-arguments, which is exactly what the compliance
   self-critique requires.

3. At Q3_K_S quantization (3.16 GB), it runs on consumer hardware
   with 8 GB RAM while maintaining acceptable output quality for
   formal government document processing.

A Q4_K_M quantization is recommended if VRAM allows, as it produces
more consistent structured outputs with fewer empty responses.

**Why not separate models per agent?** LM Studio serves one model at
a time in its basic configuration. Using one model for all agents
simplifies deployment while still demonstrating multi-agent
orchestration — the agents differ in their prompts, roles, and
memory access, not in the underlying model weights.

---

## Memory Design

Two memory layers are implemented, inspired by Praison AI's memory
architecture:

**Long-term memory** (`memory/long_term_memory.json`)
- Persists across runs to disk as a JSON key-value store
- Key: document filename (e.g. "sample_gr")
- Value: extracted obligations, deadlines, authorities, timestamp
- On subsequent runs with the same document, the Planner agent
  recalls this memory and injects it into its planning prompt,
  preventing redundant extraction work
- Demonstrated by `memory_used=True` in Planner output on run 2+

**Episodic memory** (session-scoped list in `PraisonMemory`)
- Every agent logs its actions with `memory.add_episode()`
- Captures: agent name, action taken, result summary, timestamp
- Written to `audit_log_*.json` under `episodic_memory` key
- Enables post-run analysis of exactly what each agent did
  and in what order

**Cross-agent memory** (`WorkflowState.cross_agent_memory`)
- A shared dictionary accessible to all agents during a run
- Stores: analysis summary, draft history, compliance results,
  document comparison results, message bus log
- Agents read each other's summaries without re-running extraction

---

## How Hermes Agent, DeerFlow 2, and Praison AI Are Combined

The three frameworks address three distinct problems:

**Praison AI → Orchestration and memory**
Praison AI's core value is conversational multi-agent orchestration
with built-in memory. We implement this concept via `PraisonMemory`
(long-term + episodic) and the WorkflowState shared object. Every
agent reads from and writes to shared memory. The multi-round
drafting ↔ compliance negotiation loop is Praison AI's
conversational orchestration pattern applied to document compliance.

**DeerFlow 2 → Conditional workflow execution**
DeerFlow 2's visual flow engine represents workflows as directed
graphs with conditional edges. Our `WorkflowGraph` class implements
this exactly: 7 nodes, each with an optional condition function
that reads WorkflowState to decide whether to execute. The
`replan_workflow()` function implements DeerFlow's signature
capability — inserting new nodes mid-execution when problems are
detected (ambiguous documents, failed compliance, missing fields).

**Hermes Agent → Meta-reasoning and few-shot adaptation**
The Nous-Hermes-2 model is specifically used for:
- Self-critique: the compliance agent asks the model to generate
  counter-arguments against its own draft (`_hermes_self_critique`)
- Few-shot adaptation: document type is detected and a matching
  example is injected into the drafting prompt, allowing the model
  to adapt to new circular types without retraining

**Combined behaviours this enables:**
- A document seen before is processed faster (Praison memory)
- Workflow adjusts itself when the document is unusual (DeerFlow)
- The draft is critiqued without human intervention (Hermes)
- All three happen in the same run, coordinated by the orchestrator

---

## Failure Case Handling

| Failure | Detection | Behaviour |
|---|---|---|
| Partial / scanned PDF | `len(pdf_text) < 100` | Fallback activated, placeholder obligations inserted, ambiguity flagged |
| No obligations extracted | `len(obligations) == 0` | Flagged as ambiguous, DeerFlow inserts "Deep obligation search" node |
| LLM returns empty response | `not response.choices` | Warning logged, fallback draft generated from structured template |
| LM Studio offline | `except Exception` in `_ask()` | Error caught, logged to `state.error_log`, graceful exit with message |
| Compliance never passes | `iteration >= max_iterations` | Outputs generated anyway with `compliance_passed=False` and full issue list |
| Contradictory documents | Multi-doc comparison tool | Contradictions extracted and listed in compliance report |
| Model name mismatch | API error caught | Clear error message with instructions to check model name |

All failures are written to `audit_log_*.json` under `error_log`
so the full failure history is always preserved.

---

## Future Scalability Considerations

**1. True multi-model orchestration**
Replace LM Studio with vLLM or Ollama running multiple models
simultaneously. Assign specialist models per agent: a legal
fine-tuned model for analysis, Hermes for compliance critique,
a smaller fast model for planning.

**2. Vector database for semantic memory**
Replace the JSON-based long-term memory with ChromaDB or FAISS.
Enable semantic search: "find past GRs similar to this one"
rather than exact filename matching. This scales to hundreds of
past documents.

**3. Parallel agent execution**
The current pipeline is sequential. Analysis, Planner, and
Drafting could run in parallel using Python asyncio once the
PDF extraction is complete. This would cut runtime by ~40%.

**4. Real DeerFlow 2 integration**
As DeerFlow 2 matures and gains a stable pip-installable API,
the `deerflow/` folder can be replaced with the real framework
while keeping all agent code unchanged.

**5. Streamlit → FastAPI + React**
The Streamlit UI is suitable for demos. A production deployment
would use FastAPI as the backend and a React frontend, enabling
multiple concurrent users and real-time websocket updates.

**6. Regional language support**
Add a translation pre-processing step using IndicTrans2 or
similar to handle circulars in Hindi, Marathi, or other
regional languages before extraction.

**7. Digital signature validation**
Integrate with government PKI infrastructure to validate
the digital signatures on official PDF circulars before
processing, ensuring authenticity.