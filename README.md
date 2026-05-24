# Government AI Multi-Agent Assistant
A locally running multi-agent AI system that simulates an internal
Government Officer Assistant. Processes Government Resolutions (GRs)
and Circulars using four coordinated AI agents powered by
Nous-Hermes-2, PraisonAI memory, and a DeerFlow-style workflow graph.
## Architecture
Four agents communicate via a shared WorkflowState and a MessageBus:
| Agent | Role | Framework used |
| Planner | Decomposes task, builds workflow graph | DeerFlow 2 |
| Analysis | Extracts obligations, deadlines, authorities | Hermes in-context |
| Drafting | Writes formal government response | Hermes few-shot |
| Compliance | Validates draft, runs self-critique | Hermes meta-reasoning |

Extended capabilities: PraisonAI long-term + episodic memory,
DeerFlow dynamic replanning, Hermes self-critique, multi-round
negotiation, automated audit trail, few-shot policy adaptation.
## Requirements
- Windows 10/11
- Python 3.10 or higher
- LM Studio (free) with Nous-Hermes-2-Mistral-7B-DPO loaded
- 8 GB RAM minimum (16 GB recommended)
- ~5 GB disk space for the model
## Setup
### Step 1 — LM Studio
1. Download LM Studio from https://lmstudio.ai
2. Search for `nous-hermes-2-mistral-7b-dpo`
3. Download the Q3_K_S or Q4_K_M quantized version
4. Go to Local Server tab → Start Server (port 1234)
5. Confirm server is running at http://127.0.0.1:1234/v1/models

### Step 2 — Python environment
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
### Step 3 — Verify connection

```powershell
python -c "
from openai import OpenAI
c = OpenAI(base_url='http://127.0.0.1:1234/v1', api_key='lm-studio')
r = c.chat.completions.create(
    model='nous-hermes-2-mistral-7b-dpo',
    messages=[{'role':'user','content':'Say hello'}],
    max_tokens=20
)
print(r.choices[0].message.content)
"
```

### Step 4 — Check model name in config.py

```powershell
python -c "
from openai import OpenAI
c = OpenAI(base_url='http://127.0.0.1:1234/v1', api_key='lm-studio')
[print(m.id) for m in c.models.list().data]
"
Copy the exact model ID and paste it into `config.py` for all three model fields.

## Running

### Terminal (command line)

```powershell
# Single document
python main.py sample_docs\sample_gr.pdf

# Two documents (multi-document comparison)
python main.py sample_docs\sample_gr.pdf --pdf2 sample_docs\sample_gr2.pdf
```

### Streamlit UI (browser)

```powershell
streamlit run app.py
```

Opens at http://localhost:8501

---

## Output Files

Every run generates 7 files in the `outputs/` folder:

| File | Contents |
|---|---|
| `draft_*.txt` | Official government response letter |
| `summary_*.json` | Structured JSON with all extracted fields |
| `compliance_report_*.txt` | Validation report with Hermes critique |
| `confidence_*.json` | Confidence score and threshold result |
| `reasoning_*.txt` | Step-by-step agent reasoning log |
| `audit_log_*.json` | Full audit trail + message bus log |
| `schema_validation_*.json` | JSON schema enforcement result |

---

## Extended Capabilities Demonstrated

1. **Dynamic workflow replanning** — DeerFlow graph inserts new nodes
   mid-execution when ambiguities are detected
2. **Hermes self-critique** — Compliance agent uses Hermes model to
   generate counter-arguments against its own draft
3. **Praison AI cross-agent memory** — Long-term memory persists GR
   interpretations across runs; episodic memory logs session actions
4. **Multi-round negotiation** — Drafting and Compliance agents
   negotiate across up to 3 iterations
5. **Automated audit trail** — Every agent action timestamped to JSON
6. **Few-shot policy adaptation** — Document type detected and
   matching example injected into drafting prompt

---

## Configuration

Edit `config.py` to change:

```python
LM_STUDIO_BASE_URL   = "http://127.0.0.1:1234/v1"
HERMES_MODEL         = "nous-hermes-2-mistral-7b-dpo"
GENERAL_MODEL        = "nous-hermes-2-mistral-7b-dpo"
PLANNER_MODEL        = "nous-hermes-2-mistral-7b-dpo"
MAX_ITERATIONS       = 3
COMPLIANCE_THRESHOLD = 0.80
