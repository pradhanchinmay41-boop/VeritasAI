"""
app.py
------
Enterprise AI Research Agent — Modern Streamlit Executive Interface

Features:
  1. 🚀 New Research Studio    -- Preset industry topics, customizable depth, live 7-stage progress visualizer
  2. 📄 Traceable Report       -- Full evidence provenance (Conclusions -> Supporting Claims -> Web Sources), interactive filters & exports (MD, JSON, HTML)
  3. 📚 Knowledge Base Index   -- Persistent SQLite index search, status filters & analytics dashboard
  4. 🔍 Claims & Evidence Search-- Global cross-topic finder for extracted atomic factual claims and sources
  5. ⚙️ System & Backend Radar -- Real-time latency & health inspector, custom backend URL config

Run with:  streamlit run frontend/app.py
"""

import os
import time
import json
import requests
import datetime
import streamlit as st

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="VeritasAI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "backend_url" not in st.session_state:
    st.session_state["backend_url"] = os.environ.get("BACKEND_URL", "http://localhost:8000")
if "last_topic_id" not in st.session_state:
    st.session_state["last_topic_id"] = None

BACKEND_URL = st.session_state["backend_url"]

# ---------------------------------------------------------
# Modern Executive Visual Styling (CSS)
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    h1, h2, h3, .main-title {
        font-family: 'Outfit', 'Inter', sans-serif !important;
    }

    /* Enterprise Hero Header */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem 2.2rem;
        border-radius: 16px;
        color: #f8fafc;
        margin-bottom: 2rem;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .hero-banner::before {
        content: "";
        position: absolute;
        top: -50%;
        right: -10%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, rgba(0,0,0,0) 70%);
        pointer-events: none;
    }

    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #ffffff 0%, #cbd5e1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        max-width: 800px;
        line-height: 1.5;
        margin-bottom: 0;
    }

    /* Metric Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.25rem;
        transition: all 0.2s ease-in-out;
    }
    
    .metric-card:hover {
        border-color: rgba(59, 130, 246, 0.4);
        transform: translateY(-2px);
    }

    /* Status Badges */
    .badge-confidence-high {
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    
    .badge-confidence-medium {
        background-color: rgba(234, 179, 8, 0.15);
        color: #facc15;
        border: 1px solid rgba(234, 179, 8, 0.3);
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }

    .badge-confidence-low {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }

    .category-pill {
        background: #334155;
        color: #e2e8f0;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Traceability Source Cards */
    .finding-card {
        background-color: rgba(15, 23, 42, 0.6);
        border-left: 4px solid #3b82f6;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding: 1rem 1.25rem;
        border-radius: 0 10px 10px 0;
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
    }

    .finding-card-strong { border-left-color: #22c55e; }
    .finding-card-moderate { border-left-color: #3b82f6; }
    .finding-card-weak { border-left-color: #f59e0b; }

    /* Contradiction Box */
    .contradiction-container {
        background: linear-gradient(135deg, rgba(225, 29, 72, 0.08) 0%, rgba(159, 18, 57, 0.05) 100%);
        border: 1px solid rgba(244, 63, 94, 0.3);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Helper API Functions with Caching & Error Handling
# ---------------------------------------------------------
@st.cache_data(ttl=3)
def fetch_topics_cached(backend_url):
    r = requests.get(f"{backend_url}/topics", timeout=10)
    r.raise_for_status()
    return r.json()

def api_get(path):
    url = f"{st.session_state['backend_url']}{path}"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json()

def api_post(path, json_body):
    url = f"{st.session_state['backend_url']}{path}"
    r = requests.post(url, json=json_body, timeout=600)
    r.raise_for_status()
    return r.json()

def get_backend_health():
    start = time.time()
    try:
        r = requests.get(f"{st.session_state['backend_url']}/health", timeout=5)
        latency = int((time.time() - start) * 1000)
        if r.status_code == 200:
            return True, f"Online ({latency} ms)", latency
    except Exception as e:
        return False, str(e), 0
    return False, "Unknown Error", 0

# ---------------------------------------------------------
# Header Banner
# ---------------------------------------------------------
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">⚡ VeritasAI</div>
    <div class="hero-subtitle">
        An enterprise AI research agent.
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar System Dashboard
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ System Control Radar")
    
    # Backend URL Configuration
    url_input = st.text_input("Backend API Endpoint", value=st.session_state["backend_url"])
    if url_input != st.session_state["backend_url"]:
        st.session_state["backend_url"] = url_input
        st.rerun()

    is_online, health_msg, latency_ms = get_backend_health()
    if is_online:
        st.success(f"🟢 **Backend**: {health_msg}")
    else:
        st.error(f"🔴 **Backend Offline**: {health_msg}")

    st.markdown("---")
    st.markdown("#### 🧩 7-Stage Intelligence Pipeline")
    st.markdown("""
    1. 🎯 **Topic Decomposition** (Sub-questions)
    2. 🌐 **Targeted Web Search** (Serper/DDG)
    3. 💾 **SQLite Raw Persistence** (Sources)
    4. 🔬 **Atomic Claim Extraction** (Findings)
    5. 🏷️ **Categorization & Strength Tagging**
    6. ⚡ **Contradiction Detection** (Evidence Pairs)
    7. 💡 **Synthesis with Provenance Citations**
    """)
    
    st.markdown("---")
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    with c_s2:
        if st.button("🧹 Clear State"):
            st.session_state["last_topic_id"] = None
            st.rerun()

    st.caption("Powered by FastAPI + LLaMA-3.3-70B + SQLite")

# ---------------------------------------------------------
# Main Tabs Navigation
# ---------------------------------------------------------
tab_new, tab_report, tab_kb, tab_explorer = st.tabs([
    "🚀 New Research Studio", 
    "📄 Traceable Report", 
    "📚 Knowledge Base Index", 
    "🔍 Claims Explorer"
])

# =========================================================
# TAB 1: NEW RESEARCH STUDIO
# =========================================================
with tab_new:
    st.subheader("Launch a New Autonomous Investigation")
    st.caption("Enter any custom research inquiry or choose an enterprise preset to initiate the 7-stage live research agent.")

    st.markdown("**Executive Quick Presets:**")
    preset_cols = st.columns(4)
    preset_topic = None
    if preset_cols[0].button("🛒 AI in Retail Operations"):
        preset_topic = "How is AI transforming retail operations and inventory management?"
    if preset_cols[1].button("🏭 Smart Manufacturing AI"):
        preset_topic = "What AI technologies are revolutionizing predictive maintenance in manufacturing?"
    if preset_cols[2].button("🏥 Healthcare Automation"):
        preset_topic = "How is Generative AI improving healthcare administrative workflows and clinical trials?"
    if preset_cols[3].button("⚡ Renewable Energy Grid"):
        preset_topic = "What role does machine learning play in smart grid optimization and renewable energy?"

    default_question = preset_topic if preset_topic else ""

    with st.form("research_form", clear_on_submit=False):
        question = st.text_input(
            "Research Query / Enterprise Question",
            value=default_question,
            placeholder='e.g., "What are the latest enterprise adoption trends for agentic AI architectures?"',
            help="Enter a broad or complex research question. The agent will split it into targeted sub-questions."
        )
        
        fc1, fc2 = st.columns(2)
        with fc1:
            num_sub_q = st.slider("Sub-Questions Count", min_value=3, max_value=8, value=5, help="Number of distinct analytical dimensions to explore.")
        with fc2:
            results_per_q = st.slider("Search Depth (Results per Sub-Question)", min_value=2, max_value=8, value=4, help="Web search depth for each sub-question.")

        submitted = st.form_submit_button("🚀 Run Multi-Stage Research Agent", type="primary", use_container_width=True)

    if submitted and question.strip():
        st.markdown("---")
        st.markdown("### ⚙️ Pipeline Live Progress Monitor")
        
        progress_bar = st.progress(0, text="Initializing Research Pipeline...")
        
        status_box = st.status("Executing Research Agent Pipeline...", expanded=True)
        with status_box:
            st.write("📌 **Stage 1**: Decomposing research topic into structured sub-questions...")
            progress_bar.progress(15, text="Decomposing research topic...")

            st.write("🌐 **Stage 2 & 3**: Executing web search queries & caching raw sources in SQLite...")
            progress_bar.progress(35, text="Gathering web evidence & caching raw sources...")

            st.write("🔬 **Stage 4**: Extracting atomic factual claims from retrieved text snippets...")
            progress_bar.progress(60, text="Extracting atomic factual findings...")

            st.write("⚖️ **Stage 5 & 6**: Categorizing findings & scanning for evidence contradictions...")
            progress_bar.progress(80, text="Comparing findings & scanning for contradictions...")

            st.write("💡 **Stage 7**: Synthesizing final conclusions with explicit citation lineage...")
            progress_bar.progress(95, text="Synthesizing final conclusions...")

            try:
                result = api_post("/topics", {
                    "question": question.strip(),
                    "num_sub_questions": num_sub_q,
                    "results_per_subquestion": results_per_q,
                })
                progress_bar.progress(100, text="Pipeline Execution Complete!")
                status_box.update(label="✅ Research Pipeline Completed Successfully!", state="complete")
                
                st.session_state["last_topic_id"] = result["topic_id"]
                st.cache_data.clear()
                
                st.balloons()
                st.success(
                    f"🎉 **Research Complete!** Topic #{result['topic_id']} generated **{result['sub_questions']} sub-questions**, "
                    f"analyzed **{result['sources']} sources**, extracted **{result['findings']} factual claims**, "
                    f"flagged **{result['contradictions']} contradictions**, and derived **{result['conclusions']} traceable conclusions**."
                )
                
                st.info("👉 Switch to the **Traceable Report** tab to inspect the complete findings and citation links.")
            except Exception as e:
                progress_bar.progress(0, text="Pipeline Error")
                status_box.update(label="❌ Pipeline Execution Failed", state="error")
                st.error(f"Execution Failure: {e}")

    elif submitted:
        st.warning("⚠️ Please provide a valid research question.")

# =========================================================
# TAB 2: TRACEABLE REPORT & EVIDENCE LINEAGE
# =========================================================
with tab_report:
    st.subheader("Traceable Research Report & Provenance Lineage")
    st.caption("Every conclusion is tied to specific atomic findings, which trace directly back to stored web source URLs and snippets.")

    all_topics = []
    try:
        all_topics = fetch_topics_cached(st.session_state["backend_url"])
    except Exception as e:
        st.error(f"Could not load topics from backend: {e}")

    if not all_topics:
        st.info("No research reports stored yet. Launch your first investigation in the 'New Research Studio' tab!")
    else:
        topic_options = {f"#{t['id']} — {t['question']}": t["id"] for t in all_topics}
        
        # Select active topic
        default_id = st.session_state.get("last_topic_id")
        default_index = 0
        if default_id:
            for idx, (label, tid) in enumerate(topic_options.items()):
                if tid == default_id:
                    default_index = idx
                    break

        selected_label = st.selectbox(
            "Select Investigation Topic",
            options=list(topic_options.keys()),
            index=default_index,
            key="report_topic_selector"
        )
        active_topic_id = topic_options[selected_label]

        report = None
        try:
            report = api_get(f"/topics/{active_topic_id}/report")
        except Exception as e:
            st.error(f"Error fetching report #{active_topic_id}: {e}")

        if report:
            topic_data = report["topic"]
            
            st.markdown(f"## 🎯 {topic_data['question']}")
            st.caption(f"Topic ID: **#{topic_data['id']}** | Status: **{topic_data['status'].upper()}** | Created: **{topic_data['created_at'][:19].replace('T', ' ')} UTC**")

            # Overview KPIs
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Sub-Questions Planned", len(report["sub_questions"]))
            k2.metric("Sources Analyzed", report["all_sources_count"])
            k3.metric("Atomic Claims Extracted", report["all_findings_count"])
            k4.metric("Contradictions Flagged", len(report["contradictions"]))

            st.markdown("---")

            # Section 1: Research Strategy & Plan
            with st.expander("📌 View Research Strategy & Sub-Questions", expanded=False):
                st.markdown("#### Research Sub-Questions Strategy:")
                for sq in report["sub_questions"]:
                    cat_name = sq.get('category', 'general').upper()
                    st.markdown(f"- `<span class=\"category-pill\">{cat_name}</span>` **{sq['text']}**", unsafe_allow_html=True)

            # Section 2: Interactive Finding Filters & Controls
            st.markdown("### 💡 Synthesized Conclusions & Evidence Provenance")
            
            filter_c1, filter_c2 = st.columns([1, 2])
            with filter_c1:
                strength_filter = st.multiselect(
                    "Filter Evidence Strength",
                    options=["strong", "moderate", "weak"],
                    default=["strong", "moderate", "weak"],
                    format_func=lambda x: {"strong": "💪 Strong", "moderate": "⚖️ Moderate", "weak": "🔍 Weak"}[x]
                )
            
            if not report["conclusions"]:
                st.warning("No conclusions available for this topic yet.")
            else:
                for idx, c in enumerate(report["conclusions"], 1):
                    conf = c.get("confidence", "medium")
                    badge_class = {
                        "high": "badge-confidence-high",
                        "medium": "badge-confidence-medium",
                        "low": "badge-confidence-low"
                    }.get(conf, "badge-confidence-medium")

                    badge_html = f'<span class="{badge_class}">Confidence: {conf.upper()}</span>'

                    with st.expander(f"Conclusion #{idx}: {c['text']}", expanded=True):
                        st.markdown(f"**Confidence Rating**: {badge_html}", unsafe_allow_html=True)
                        st.markdown("#### 🔬 Supporting Factual Findings & Source Provenance:")

                        findings = c.get("findings", [])
                        filtered_findings = [f for f in findings if f.get("strength", "moderate") in strength_filter]

                        if not filtered_findings:
                            st.info("No findings matching the selected strength filters.")
                        else:
                            for f in filtered_findings:
                                src = f.get("source") or {}
                                strength = f.get("strength", "moderate")
                                strength_icon = {"strong": "💪 Strong", "moderate": "⚖️ Moderate", "weak": "🔍 Weak"}.get(strength, strength)
                                category = f.get("category", "general").upper()
                                
                                border_class = f"finding-card-{strength}"
                                url = src.get('url', '#')
                                title = src.get('title') or url
                                snippet = src.get('snippet', 'No snippet available')

                                st.markdown(f"""
                                <div class="finding-card {border_class}">
                                    <div style="font-size: 1.05rem; font-weight: 600; margin-bottom: 6px; color: #f8fafc;">
                                        "{f['text']}"
                                    </div>
                                    <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 8px;">
                                        <span class="category-pill">{category}</span>
                                        <span style="font-size: 0.85rem; color: #94a3b8;">Evidence Strength: <strong>{strength_icon}</strong></span>
                                        <span style="font-size: 0.85rem; color: #64748b;">Finding ID: #{f['id']}</span>
                                    </div>
                                    <div style="font-size: 0.88rem; color: #cbd5e1; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px;">
                                        🔗 <strong>Source:</strong> <a href="{url}" target="_blank" style="color: #60a5fa; text-decoration: underline;">{title}</a><br/>
                                        <span style="color: #94a3b8; font-style: italic;">"{snippet}"</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

            # Section 3: Flagged Contradictions Matrix
            if report["contradictions"]:
                st.markdown("---")
                st.markdown("### ⚠️ Flagged Evidence Contradictions")
                st.caption("Automated cross-source validation flagged conflicting claims:")

                for c in report["contradictions"]:
                    fa, fb = c.get("finding_a"), c.get("finding_b")
                    st.markdown(f"""
                    <div class="contradiction-container">
                        <h4 style="color: #fb7185; margin-top: 0; margin-bottom: 8px;">⚡ Contradiction Detected: {c['explanation']}</h4>
                        <div style="display: flex; gap: 1rem; margin-top: 0.75rem;">
                            <div style="flex: 1; background: rgba(15, 23, 42, 0.7); padding: 0.85rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                                <strong style="color: #60a5fa;">Claim A (Finding #{c['finding_a_id']}):</strong><br/>
                                <span style="color: #e2e8f0;">"{fa['text'] if fa else 'N/A'}"</span>
                            </div>
                            <div style="flex: 1; background: rgba(15, 23, 42, 0.7); padding: 0.85rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                                <strong style="color: #f472b6;">Claim B (Finding #{c['finding_b_id']}):</strong><br/>
                                <span style="color: #e2e8f0;">"{fb['text'] if fb else 'N/A'}"</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Section 4: Export Center
            st.markdown("---")
            st.markdown("### 📥 Report Export Center")
            exp_c1, exp_c2, exp_c3 = st.columns(3)

            # Markdown Generator
            md_content = f"# Research Report: {topic_data['question']}\n"
            md_content += f"*Generated by Enterprise AI Research Agent on {topic_data['created_at']}*\n\n"
            md_content += "## Conclusions & Evidence Provenance\n\n"
            for idx, c in enumerate(report["conclusions"], 1):
                md_content += f"### Conclusion {idx}: {c['text']}\n"
                md_content += f"- **Confidence**: {c.get('confidence', 'medium')}\n"
                md_content += "- **Supporting Findings**:\n"
                for f in c.get("findings", []):
                    src = f.get("source") or {}
                    md_content += f"  - \"{f['text']}\" (Category: {f.get('category')}, Strength: {f.get('strength')})\n"
                    md_content += f"    Source: [{src.get('title', 'Link')}]({src.get('url', '#')})\n"
                md_content += "\n"

            if report["contradictions"]:
                md_content += "## Flagged Contradictions\n\n"
                for c in report["contradictions"]:
                    md_content += f"- **Conflict**: {c['explanation']}\n"

            # Downloads
            exp_c1.download_button(
                label="📄 Download Markdown (.md)",
                data=md_content,
                file_name=f"research_report_{active_topic_id}.md",
                mime="text/markdown",
                use_container_width=True
            )

            exp_c2.download_button(
                label="📦 Download JSON Data (.json)",
                data=json.dumps(report, indent=2),
                file_name=f"research_report_{active_topic_id}.json",
                mime="application/json",
                use_container_width=True
            )

            # Formatted HTML generator
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Research Report #{active_topic_id}</title>
                <style>
                    body {{ font-family: system-ui, sans-serif; padding: 2rem; max-width: 900px; margin: 0 auto; color: #1e293b; line-height: 1.6; }}
                    h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }}
                    .conclusion {{ background: #f8fafc; border-left: 4px solid #3b82f6; padding: 1rem; margin-bottom: 1.5rem; border-radius: 4px; }}
                    .finding {{ background: white; padding: 0.75rem; border: 1px solid #e2e8f0; margin-top: 0.5rem; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <h1>Enterprise Research Report</h1>
                <h2>Topic: {topic_data['question']}</h2>
                <p><em>Created: {topic_data['created_at']}</em></p>
                <hr/>
                <h3>Synthesized Conclusions</h3>
                {"".join([f'<div class="conclusion"><h4>Conclusion: {c["text"]}</h4><p><strong>Confidence:</strong> {c.get("confidence")}</p>' + "".join([f'<div class="finding"><strong>Claim:</strong> "{f["text"]}"<br/><small>Source: <a href="{f.get("source",{}).get("url","#")}">{f.get("source",{}).get("title","Link")}</a></small></div>' for f in c.get("findings",[])]) + '</div>' for c in report["conclusions"]])}
            </body>
            </html>
            """
            
            exp_c3.download_button(
                label="🌐 Download Executive HTML (.html)",
                data=html_content,
                file_name=f"research_report_{active_topic_id}.html",
                mime="text/html",
                use_container_width=True
            )

# =========================================================
# TAB 3: KNOWLEDGE BASE INDEX
# =========================================================
with tab_kb:
    st.subheader("Persistent Knowledge Base Index")
    st.caption("All research topics, raw web sources, and extracted atomic claims persist permanently in SQLite across server restarts.")

    topics = []
    try:
        topics = fetch_topics_cached(st.session_state["backend_url"])
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")

    if not topics:
        st.info("No research topics stored yet. Run a pipeline in the 'New Research Studio' tab!")
    else:
        # Knowledge Base Overview Metrics
        completed_count = sum(1 for t in topics if t.get("status") == "done")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Researched Topics", len(topics))
        m2.metric("Completed Investigations", completed_count)
        m3.metric("Storage Engine", "SQLite (research.db)")
        m4.metric("Pipeline Success Rate", f"{int((completed_count / len(topics)) * 100)}%")

        st.markdown("---")

        # Filtering & Search Bar
        kb_col1, kb_col2 = st.columns([3, 1])
        with kb_col1:
            search_query = st.text_input("🔍 Filter Knowledge Base Topics by Keyword", "", key="kb_search_input")
        with kb_col2:
            status_filter = st.selectbox("Status Filter", ["All", "done", "running", "error", "pending"], key="kb_status_filter")

        filtered = topics
        if search_query:
            filtered = [t for t in filtered if search_query.lower() in t["question"].lower()]
        if status_filter != "All":
            filtered = [t for t in filtered if t.get("status") == status_filter]

        st.markdown(f"Displaying **{len(filtered)}** of **{len(topics)}** topics:")

        for t in filtered:
            status = t.get("status", "unknown")
            status_icon = {
                "done": "✅ Complete",
                "running": "⏳ Executing",
                "error": "❌ Error",
                "pending": "⏸️ Pending"
            }.get(status, status)

            with st.container():
                tc1, tc2, tc3, tc4 = st.columns([5, 2, 2, 2])
                tc1.markdown(f"**#{t['id']} — {t['question']}**")
                tc2.caption(f"Created: {t['created_at'][:19].replace('T', ' ')}")
                tc3.markdown(f"`{status_icon}`")
                
                if tc4.button("Open Report", key=f"btn_open_kb_{t['id']}", use_container_width=True):
                    st.session_state["last_topic_id"] = t["id"]
                    st.info(f"Loaded Topic #{t['id']}. Switch to the 'Traceable Report' tab to view details.")

# =========================================================
# TAB 4: CLAIMS & EVIDENCE EXPLORER
# =========================================================
with tab_explorer:
    st.subheader("Global Claims & Evidence Explorer")
    st.caption("Search directly across atomic factual claims and extracted web evidence stored in the SQLite knowledge base.")

    claim_query = st.text_input("🔎 Search atomic claims & snippets by keyword", placeholder="e.g. retail, maintenance, inventory, cost, accuracy...", key="global_claim_search")
    
    all_kb_topics = []
    try:
        all_kb_topics = fetch_topics_cached(st.session_state["backend_url"])
    except Exception:
        pass

    if claim_query and all_kb_topics:
        st.markdown(f"Searching across all topics for keyword: `'{claim_query}'`...")
        matches_found = 0

        for t in all_kb_topics:
            try:
                findings = api_get(f"/topics/{t['id']}/findings")
                matching = [f for f in findings if claim_query.lower() in f.get("text", "").lower() or claim_query.lower() in f.get("category", "").lower()]
                
                if matching:
                    matches_found += len(matching)
                    with st.expander(f"Topic #{t['id']}: {t['question']} ({len(matching)} matches)", expanded=True):
                        for f in matching:
                            cat = f.get("category", "general").upper()
                            str_val = f.get("strength", "moderate")
                            st.markdown(f"""
                            <div class="finding-card finding-card-{str_val}">
                                <span class="category-pill">{cat}</span>
                                <span style="font-size: 0.85rem; color: #94a3b8; margin-left: 8px;">Strength: {str_val.upper()}</span>
                                <div style="margin-top: 6px; font-size: 0.95rem; color: #f8fafc;">
                                    "{f['text']}"
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
            except Exception:
                continue

        if matches_found == 0:
            st.warning(f"No atomic claims found matching '{claim_query}'.")
        else:
            st.success(f"Found {matches_found} matching claim(s) across stored topics!")
    elif not claim_query:
        st.info("Enter a keyword above to search through the entire database of extracted factual claims.")
