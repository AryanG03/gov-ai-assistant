"""
Streamlit UI — Government AI Multi-Agent Assistant
"""
import streamlit as st
import os
import json
import tempfile
import datetime
import sys

# Page config
st.set_page_config(
    page_title="Government AI Assistant",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a365d;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #4a5568;
        margin-bottom: 2rem;
    }
    .framework-badge {
        display: inline-block;
        background: #ebf8ff;
        color: #2b6cb0;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .metric-card {
        background: #f7fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .status-passed {
        background: #f0fff4;
        border: 1px solid #9ae6b4;
        border-radius: 8px;
        padding: 1rem;
        color: #276749;
        font-weight: 600;
        text-align: center;
        font-size: 1.2rem;
    }
    .status-failed {
        background: #fff5f5;
        border: 1px solid #feb2b2;
        border-radius: 8px;
        padding: 1rem;
        color: #9b2335;
        font-weight: 600;
        text-align: center;
        font-size: 1.2rem;
    }
    .agent-step {
        background: #f7fafc;
        border-left: 4px solid #4299e1;
        padding: 0.5rem 1rem;
        margin: 0.3rem 0;
        border-radius: 0 6px 6px 0;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .obligation-item {
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 0.5rem 0.8rem;
        margin: 0.3rem 0;
        font-size: 0.9rem;
    }
    .issue-item {
        background: #fffaf0;
        border-left: 3px solid #ed8936;
        padding: 0.4rem 0.8rem;
        margin: 0.3rem 0;
        font-size: 0.85rem;
        border-radius: 0 4px 4px 0;
    }
    .download-section {
        background: #f7fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">🏛️ Government AI Multi-Agent Assistant</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sub-header">Analyze Government Resolutions & Circulars using local AI</div>',
            unsafe_allow_html=True)

st.markdown("""
<span class="framework-badge">🧠 PraisonAI Memory</span>
<span class="framework-badge">🔀 DeerFlow Workflow</span>
<span class="framework-badge">⚡ Hermes Self-Critique</span>
""", unsafe_allow_html=True)

st.divider()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("LM Studio")
    lm_url = st.text_input(
        "Server URL",
        value="http://127.0.0.1:1234/v1",
        help="Your LM Studio local server URL"
    )
    model_name = st.text_input(
        "Model Name",
        value="nous-hermes-2-mistral-7b-dpo",
        help="Exact model name as shown in LM Studio"
    )

    st.subheader("Orchestration")
    max_iterations = st.slider(
        "Max Iterations", 1, 5, 3,
        help="Maximum compliance refinement rounds"
    )
    compliance_threshold = st.slider(
        "Compliance Threshold", 0.5, 1.0, 0.80, 0.05,
        help="Minimum score to pass compliance"
    )

    st.divider()

    # LM Studio connection check
    st.subheader("🔌 Connection Status")
    if st.button("Check LM Studio", use_container_width=True):
        try:
            from openai import OpenAI
            client = OpenAI(base_url=lm_url, api_key="lm-studio")
            models = client.models.list()
            if models.data:
                st.success(f"✅ Connected\n{models.data[0].id}")
            else:
                st.error("❌ No models loaded")
        except Exception as e:
            st.error(f"❌ Cannot connect\n{e}")

    st.divider()
    st.caption("Government AI Multi-Agent Assistant v1.0")
    st.caption("Models run locally via LM Studio")


# ── Main area ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📄 Primary Document")
    uploaded_file = st.file_uploader(
        "Upload Government Resolution / Circular (PDF)",
        type=["pdf"],
        key="primary_pdf",
    )
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name} ({uploaded_file.size:,} bytes)")

with col2:
    st.subheader("📄 Second Document (Optional)")
    uploaded_file2 = st.file_uploader(
        "Upload second circular for comparison",
        type=["pdf"],
        key="secondary_pdf",
        help="Used for multi-document contradiction detection"
    )
    if uploaded_file2:
        st.success(f"✅ {uploaded_file2.name} — will compare for contradictions")

st.divider()

# ── Run button ────────────────────────────────────────────────────────────────
run_col1, run_col2, run_col3 = st.columns([1, 2, 1])
with run_col2:
    run_button = st.button(
        "🚀 Run Analysis",
        use_container_width=True,
        type="primary",
        disabled=uploaded_file is None,
    )

if not uploaded_file:
    st.info("👆 Upload a Government Resolution or Circular PDF to begin.")
    st.stop()


# ── Run pipeline ──────────────────────────────────────────────────────────────
if run_button:

    # Update config dynamically
    import config
    config.LM_STUDIO_BASE_URL    = lm_url
    config.GENERAL_MODEL         = model_name
    config.HERMES_MODEL          = model_name
    config.PLANNER_MODEL         = model_name
    config.MAX_ITERATIONS        = max_iterations
    config.COMPLIANCE_THRESHOLD  = compliance_threshold

    # Save uploaded PDFs to temp files
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp1:
        tmp1.write(uploaded_file.read())
        pdf_path1 = tmp1.name

    pdf_path2 = None
    if uploaded_file2:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp2:
            tmp2.write(uploaded_file2.read())
            pdf_path2 = tmp2.name

    # ── Live progress display ─────────────────────────────────────────────────
    st.subheader("⚙️ Processing...")
    progress_bar  = st.progress(0)
    status_text   = st.empty()
    log_container = st.container()
    log_lines     = []

    def add_log(msg: str, icon: str = ""):
        log_lines.append(f"{icon} {msg}" if icon else msg)
        with log_container:
            for line in log_lines[-8:]:  # show last 8 lines
                st.markdown(f'<div class="agent-step">{line}</div>',
                            unsafe_allow_html=True)

    # ── Import and run ────────────────────────────────────────────────────────
    try:
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

        os.makedirs("outputs", exist_ok=True)
        state  = WorkflowState(pdf_path=pdf_path1, max_iterations=max_iterations)
        bus    = MessageBus()
        memory = PraisonMemory()

        # Step 1: Load PDF
        status_text.text("Step 1: Loading PDF...")
        progress_bar.progress(10)
        meta = get_pdf_metadata(pdf_path1)
        state.pdf_text = extract_text_from_pdf(pdf_path1)
        add_log(f"PDF loaded: {meta['pages']} page(s), "
                f"{len(state.pdf_text):,} chars", "📄")
        state.log_audit("orchestrator", "pdf_loaded",
                        f"pages={meta['pages']}")

        # Step 1b: Compare documents
        if pdf_path2:
            status_text.text("Comparing documents...")
            progress_bar.progress(20)
            add_log("Running multi-document comparison...", "🔍")
            state.pdf_text2 = extract_text_from_pdf(pdf_path2)
            comp = compare_documents(
                state.pdf_text, state.pdf_text2,
                uploaded_file.name,
                uploaded_file2.name,
            )
            state.contradictions = comp.get("contradictions", [])
            state.cross_agent_memory["document_comparison"] = comp
            add_log(f"Comparison complete: "
                    f"{len(state.contradictions)} contradiction(s) found", "⚠️")

        # Step 2: Analysis
        status_text.text("Step 2: Analysis Agent extracting obligations...")
        progress_bar.progress(30)
        add_log("Analysis Agent started...", "🔬")
        state = run_analysis(state, bus, memory)
        add_log(f"Extracted: {len(state.obligations)} obligations, "
                f"{len(state.deadlines)} deadlines, "
                f"{len(state.authorities)} authorities", "✅")
        progress_bar.progress(50)

        # Step 3: Orchestration loop
        graph = None
        for iteration in range(max_iterations):
            state.current_iteration = iteration
            pct = 50 + (iteration * 15)
            progress_bar.progress(min(pct, 90))
            status_text.text(
                f"Step 3: Iteration {iteration+1}/{max_iterations}...")
            add_log(f"── Iteration {iteration+1} ──", "🔄")

            state, graph = run_planner(state, bus, memory)
            add_log(f"Planner: {len(state.task_plan)} tasks, "
                    f"memory={'Yes' if memory.recall(os.path.basename(pdf_path1).replace('.pdf','')) else 'No'}", "📋")

            if iteration > 0 or state.fallback_triggered:
                graph, inserted = replan_workflow(graph, state, "n5")
                if inserted:
                    add_log(f"DeerFlow replanned: {inserted}", "🔀")

            state = run_drafting(state, bus, memory)
            add_log(f"Draft v{state.draft_version} created "
                    f"({len(state.draft_response)} chars)", "✍️")

            state = run_compliance(state, bus, memory)
            status_icon = "✅" if state.compliance_passed else "❌"
            add_log(f"Compliance: score={state.confidence_score:.2f} "
                    f"{'PASSED' if state.compliance_passed else 'FAILED'} "
                    f"| Hermes issues={len(state.self_critique)}", status_icon)

            if state.compliance_passed:
                add_log(f"Passed at iteration {iteration+1}!", "🎉")
                break
            elif iteration < max_iterations - 1:
                add_log("Negotiating next round...", "🔁")

        memory.store_gr_interpretation(
            pdf_path1, state.obligations,
            state.deadlines, state.authorities)
        add_log("Praison memory: GR stored for future runs", "🧠")

        state.workflow_complete = True
        state.cross_agent_memory["message_bus_log"] = bus.get_log()
        state.episodic_memory = memory.episodic

        # Generate outputs
        status_text.text("Generating output files...")
        progress_bar.progress(95)

        ts    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        paths = {}

        official_doc = generate_official_document(state)
        draft_path   = os.path.join("outputs", f"draft_{ts}.txt")
        with open(draft_path, "w", encoding="utf-8") as f:
            f.write(official_doc)
        paths["draft"] = draft_path

        json_path = os.path.join("outputs", f"summary_{ts}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(state.to_summary_dict(), f, indent=2, ensure_ascii=False)
        paths["json_summary"] = json_path

        comp_path = os.path.join("outputs", f"compliance_report_{ts}.txt")
        with open(comp_path, "w", encoding="utf-8") as f:
            f.write(f"COMPLIANCE REPORT\n{'='*60}\n")
            f.write(f"Status: {'PASSED' if state.compliance_passed else 'FAILED'}\n")
            f.write(f"Score: {state.confidence_score:.2f}\n")
            f.write(f"Iterations: {state.current_iteration+1}\n\n")
            f.write("OBLIGATIONS:\n")
            for o in state.obligations:
                f.write(f"  - {o}\n")
            f.write("\nDEADLINES:\n")
            for d in state.deadlines:
                f.write(f"  - {d}\n")
            f.write("\nAUTHORITIES:\n")
            for a in state.authorities:
                f.write(f"  - {a}\n")
            f.write("\nHERMES CRITIQUE:\n")
            for c in state.self_critique:
                f.write(f"  - {c}\n")
            f.write("\nCONTRADICTIONS:\n")
            for c in state.contradictions:
                f.write(f"  - {c}\n")
        paths["compliance_report"] = comp_path

        conf_path = os.path.join("outputs", f"confidence_{ts}.json")
        with open(conf_path, "w", encoding="utf-8") as f:
            json.dump({
                "confidence_score":  state.confidence_score,
                "threshold":         compliance_threshold,
                "passed":            state.compliance_passed,
                "iterations":        state.current_iteration + 1,
                "draft_version":     state.draft_version,
            }, f, indent=2)
        paths["confidence_score"] = conf_path

        reason_path = os.path.join("outputs", f"reasoning_{ts}.txt")
        with open(reason_path, "w", encoding="utf-8") as f:
            f.write("REASONING STEPS\n" + "="*60 + "\n")
            for i, step in enumerate(state.reasoning_steps, 1):
                f.write(f"Step {i:02d}: {step}\n")
        paths["reasoning_steps"] = reason_path

        audit_path = save_audit_log(
            state, state.cross_agent_memory.get("message_bus_log", []))
        paths["audit_log"] = audit_path

        progress_bar.progress(100)
        status_text.text("✅ Complete!")

        # Store in session state for display
        st.session_state["state"]  = state
        st.session_state["paths"]  = paths
        st.session_state["ts"]     = ts
        st.session_state["done"]   = True

    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())
    finally:
        # Clean up temp files
        try:
            os.unlink(pdf_path1)
            if pdf_path2:
                os.unlink(pdf_path2)
        except Exception:
            pass


# ── Results display ───────────────────────────────────────────────────────────
if st.session_state.get("done"):
    state = st.session_state["state"]
    paths = st.session_state["paths"]

    st.divider()
    st.subheader("📊 Results")

    # ── Status banner ─────────────────────────────────────────────────────────
    if state.compliance_passed:
        st.markdown(
            f'<div class="status-passed">'
            f'✅ COMPLIANCE PASSED — Score: {state.confidence_score:.2f} / 1.00'
            f'</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="status-failed">'
            f'❌ COMPLIANCE FAILED — Score: {state.confidence_score:.2f} / 1.00'
            f'</div>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Metrics row ───────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Obligations",  len(state.obligations))
    m2.metric("Deadlines",    len(state.deadlines))
    m3.metric("Authorities",  len(state.authorities))
    m4.metric("Iterations",   state.current_iteration + 1)
    m5.metric("Draft Version",state.draft_version)

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Extraction",
        "✍️ Draft",
        "🛡️ Compliance",
        "🧠 Reasoning",
        "📁 Downloads",
        "🔍 Audit Trail",
    ])

    # Tab 1: Extraction
    with tab1:
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**📌 Obligations**")
            if state.obligations:
                for ob in state.obligations:
                    st.markdown(
                        f'<div class="obligation-item">• {ob}</div>',
                        unsafe_allow_html=True)
            else:
                st.warning("No obligations extracted")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**📅 Deadlines**")
            if state.deadlines:
                for dl in state.deadlines:
                    st.markdown(
                        f'<div class="obligation-item">🗓 {dl}</div>',
                        unsafe_allow_html=True)
            else:
                st.warning("No deadlines found")

        with col_b:
            st.markdown("**🏛️ Authorities**")
            if state.authorities:
                for au in state.authorities:
                    st.markdown(
                        f'<div class="obligation-item">🏢 {au}</div>',
                        unsafe_allow_html=True)
            else:
                st.warning("No authorities found")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**👥 Applicability**")
            if state.applicability:
                for ap in state.applicability:
                    st.markdown(
                        f'<div class="obligation-item">👤 {ap}</div>',
                        unsafe_allow_html=True)
            else:
                st.warning("No applicability info found")

        if state.contradictions:
            st.divider()
            st.markdown("**⚠️ Contradictions (Multi-Document Comparison)**")
            for c in state.contradictions:
                st.markdown(
                    f'<div class="issue-item">⚠️ {c}</div>',
                    unsafe_allow_html=True)

        if state.ambiguities:
            st.divider()
            st.markdown("**❓ Ambiguities Detected**")
            for a in state.ambiguities:
                st.markdown(
                    f'<div class="issue-item">❓ {a}</div>',
                    unsafe_allow_html=True)

    # Tab 2: Draft
    with tab2:
        st.markdown(f"**Draft Version {state.draft_version}** "
                    f"({len(state.draft_response):,} characters)")
        st.text_area(
            "Official Draft Response",
            value=state.draft_response,
            height=500,
            key="draft_display",
        )
        if state.draft_history:
            st.markdown("**Draft History**")
            for dh in state.draft_history:
                st.caption(
                    f"v{dh['version']} | Iteration {dh['iteration']+1} | "
                    f"{dh['action']} | {dh['length']:,} chars")

    # Tab 3: Compliance
    with tab3:
        col_x, col_y = st.columns(2)
        with col_x:
            st.metric("Confidence Score",
                      f"{state.confidence_score:.2f}",
                      f"Threshold: {compliance_threshold}")
            st.metric("Status",
                      "PASSED" if state.compliance_passed else "FAILED")
            st.metric("Fallback Used",
                      "Yes" if state.fallback_triggered else "No")

        with col_y:
            st.metric("DeerFlow Nodes",   len(state.workflow_graph))
            st.metric("Hermes Critiques", len(state.self_critique))
            st.metric("Total Issues",     len(state.compliance_issues))

        if state.self_critique:
            st.markdown("**⚡ Hermes Self-Critique**")
            for c in state.self_critique:
                st.markdown(
                    f'<div class="issue-item">⚡ {c}</div>',
                    unsafe_allow_html=True)

        if state.compliance_issues:
            st.markdown("**🚨 Compliance Issues**")
            for issue in state.compliance_issues:
                st.markdown(
                    f'<div class="issue-item">• {issue}</div>',
                    unsafe_allow_html=True)
        else:
            st.success("No compliance issues found.")

        st.markdown("**🔀 DeerFlow Workflow Graph**")
        for node in state.workflow_graph:
            icon = "✅" if node["executed"] else "⬜"
            cond = "conditional" if node["has_condition"] else "always"
            st.caption(
                f"{icon} [{node['agent']:12}] {node['name']} ({cond})")

    # Tab 4: Reasoning
    with tab4:
        st.markdown("**Step-by-step reasoning from all agents:**")
        for i, step in enumerate(state.reasoning_steps, 1):
            agent_color = {
                "Analysis":   "#3182ce",
                "Planner":    "#805ad5",
                "Drafting":   "#d69e2e",
                "Compliance": "#e53e3e",
                "DeerFlow":   "#38a169",
            }
            color = "#4a5568"
            for agent, c in agent_color.items():
                if agent in step:
                    color = c
                    break
            st.markdown(
                f'<div class="agent-step" style="border-left-color:{color}">'
                f'<b>Step {i:02d}:</b> {step}</div>',
                unsafe_allow_html=True)

    # Tab 5: Downloads
    with tab5:
        st.markdown("**Download all generated files:**")

        file_info = [
            ("draft",            "📄 Official Draft",       "text/plain"),
            ("json_summary",     "📊 JSON Summary",         "application/json"),
            ("compliance_report","🛡️ Compliance Report",    "text/plain"),
            ("confidence_score", "📈 Confidence Score",     "application/json"),
            ("reasoning_steps",  "🧠 Reasoning Steps",      "text/plain"),
            ("audit_log",        "📋 Audit Log",            "application/json"),
        ]

        for key, label, mime in file_info:
            path = paths.get(key)
            if path and os.path.exists(path):
                with open(path, "rb") as f:
                    data = f.read()
                st.download_button(
                    label=label,
                    data=data,
                    file_name=os.path.basename(path),
                    mime=mime,
                    use_container_width=True,
                    key=f"dl_{key}",
                )

    # Tab 6: Audit Trail
    with tab6:
        st.markdown("**Complete agent action log:**")
        for entry in state.audit_trail:
            st.markdown(
                f'<div class="agent-step">'
                f'<b>[{entry["timestamp"][11:19]}]</b> '
                f'<span style="color:#805ad5">{entry["agent"]}</span> → '
                f'{entry["action"]}'
                f'{": " + entry["detail"] if entry["detail"] else ""}'
                f'</div>',
                unsafe_allow_html=True)

        if state.episodic_memory:
            st.divider()
            st.markdown("**🧠 Praison Episodic Memory (this session):**")
            for ep in state.episodic_memory:
                st.caption(
                    f"[{ep['timestamp'][11:19]}] "
                    f"{ep['agent']} → {ep['action']}: {ep['result']}")