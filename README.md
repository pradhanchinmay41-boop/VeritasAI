# Enterprise AI Research Agent
### Modus Enterprise AI Build Challenge — Assignment 9

An AI application that conducts **structured, traceable enterprise research at
scale**: give it any research topic, and it plans sub-questions, searches the
web, extracts factual findings, detects contradictions between sources, and
synthesizes conclusions — with every conclusion traceable back through the
exact findings and source URLs that support it.

This is not "ChatGPT with web search." The pipeline is a multi-stage,
narrowly-scoped process where each stage's output is persisted to a real
database before the next stage runs, so the system builds a genuinely
reusable knowledge base rather than answering once and forgetting.

---

## 1. Architecture

```
┌─────────────────────────────────────────────────────────┐
│  USER INTERFACE  (Streamlit)                             │
│  - New Research tab: enter any topic, run pipeline live  │
│  - Knowledge Base tab: browse all past topics             │
│  - Report tab: conclusions → findings → sources           │
└───────────────────────┬───────────────────────────────────┘
                         │ HTTP (REST)
┌───────────────────────▼───────────────────────────────────┐
│  APPLICATION / API LAYER  (FastAPI)                        │
│  POST /topics                — run the full pipeline       │
│  GET  /topics                — list knowledge base          │
│  GET  /topics/{id}/report    — traceable report             │
│  GET  /topics/{id}/findings  — raw findings                 │
│  GET  /topics/{id}/contradictions                           │
└───────────────────────┬───────────────────────────────────┘
                         │
┌───────────────────────▼───────────────────────────────────┐
│  AI INTELLIGENCE LAYER  (pipeline.py + llm.py)              │
│  Stage 1: Define Research Questions   (LLM call)             │
│  Stage 2: Search Sources              (Serper API)           │
│  Stage 3: Collect + Store Sources     (per sub-question)     │
│  Stage 4: Extract Findings            (LLM call, per source) │
│  Stage 5: Compare Evidence /                                 │
│           Detect Contradictions       (LLM call, per category)│
│  Stage 6: Generate Conclusions        (LLM call, cites finding│
│                                         ids for traceability)  │
│  Model: Groq LLaMA-3.3-70B via LangChain (free tier)          │
└───────────────────────┬───────────────────────────────────┘
                         │
┌───────────────────────▼───────────────────────────────────┐
│  DATA & KNOWLEDGE LAYER  (SQLite — database.py)              │
│  topics → sub_questions → sources → findings                 │
│                             ↳ contradictions                 │
│                             ↳ conclusions (cite finding ids)  │
│  Persists across restarts. Reusable research knowledge base. │
└───────────────────────┬───────────────────────────────────┘
                         │
┌───────────────────────▼───────────────────────────────────┐
│  EXTERNAL RESEARCH / DATA                                    │
│  Serper.dev (Google Search API, free tier)                   │
└─────────────────────────────────────────────────────────────┘
```

**Why each stage is a separate LLM call, not one giant prompt:** the
challenge explicitly disqualifies "a solution where all intelligence is
contained in one giant prompt." Each stage here has a narrow, auditable job —
sub-question planning, per-source extraction, per-category contradiction
detection, and final synthesis — and each writes its output to the database
before the next stage begins. If the pipeline fails partway through (e.g. one
search call errors out), everything gathered up to that point is already
persisted, not lost.

**Why conclusions cite finding IDs:** this is the traceability requirement.
The UI lets you expand any conclusion to see exactly which findings support
it, and each finding links to its exact source URL. Nothing in the final
output is an unsupported LLM assertion.

---

## 2. Technology choices (all free / open-source)

| Component      | Choice                          | Why |
|-----------------|----------------------------------|-----|
| LLM             | Groq — LLaMA-3.3-70B-versatile   | Free tier, fast inference, no card required |
| Search          | Serper.dev                      | Free tier (2,500 searches), clean JSON, no card required |
| Backend         | FastAPI + Uvicorn                | Free, open-source, async-capable |
| Database        | SQLite                          | Free, zero-setup, file-based persistence |
| Orchestration   | LangChain (`langchain-groq`)     | Free, open-source LLM client wrapper |
| Frontend        | Streamlit                        | Free, open-source, fast to build interactive UI |

**If a free-tier service becomes paid/unavailable:**
- **Groq** — swap `get_llm()` in `backend/llm.py` for another provider (Google
  Gemini free tier, or a local Ollama model). Every prompt function is
  unchanged because they all just call `get_llm().invoke(...)`.
- **Serper** — swap the body of `search()` in `backend/search.py` for Tavily's
  free tier or a DuckDuckGo HTML scrape. The rest of the pipeline is
  unaffected because it only depends on `search()` returning
  `{title, url, snippet}` dicts.

Both external dependencies are isolated to a single file each, by design.

---

## 3. Setup instructions

### Prerequisites
- Python 3.10+
- A free [Groq API key](https://console.groq.com)
- A free [Serper.dev API key](https://serper.dev)

### Steps

```bash
# 1. Clone / unzip the project, then from the project root:
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API keys
cp .env.example .env
# then edit .env and paste in your GROQ_API_KEY and SERPER_API_KEY

# 4. Start the backend (from the backend/ folder)
cd backend
uvicorn main:app --reload --port 8000

# 5. In a second terminal, start the frontend (from the frontend/ folder)
cd frontend
streamlit run app.py
```

Open the Streamlit URL it prints (usually http://localhost:8501), go to the
**New Research** tab, type any topic, and watch the pipeline run.

The database file `backend/research.db` is created automatically on first
run and persists between restarts — refreshing or restarting the app does
not erase prior research (per the challenge's data-persistence requirement).

---

## 4. The "surprise topic" / live test

The evaluator can type **any** topic into the New Research tab — nothing is
hardcoded per-topic. The pipeline:
1. Calls the LLM to break the topic into sub-questions
2. Searches the web for each sub-question via Serper
3. Extracts findings from each result
4. Compares findings within each category for contradictions
5. Synthesizes conclusions that cite specific findings

The same mechanism handles a totally new topic exactly like it handled the
demo topic — there is no per-topic branching logic anywhere in the code.

**"What happens with 1,000 topics instead of one?"** Every stage writes to
SQLite incrementally per topic; there's no in-memory global state that
grows unboundedly with topic count. Search and LLM calls are the actual
bottleneck at scale — the natural next step (noted as a limitation below)
is to move `POST /topics` to a background task queue instead of running
synchronously, and to parallelize source processing within a topic.

---

## 5. Project structure

```
enterprise-research-agent/
├── backend/
│   ├── database.py    # SQLite schema + CRUD (the knowledge base)
│   ├── search.py       # Serper API wrapper
│   ├── llm.py           # Groq/LangChain wrapper — one function per pipeline stage
│   ├── pipeline.py      # Orchestrates all stages, persists each step
│   └── main.py           # FastAPI app (the API layer)
├── frontend/
│   └── app.py             # Streamlit UI
├── requirements.txt
├── .env.example
└── README.md
```

## 6. What was built vs. AI-assisted

All architecture decisions (staged pipeline design, database schema,
traceability model via finding-ID citation, isolation of external services
into single-file wrappers) were made explicitly to satisfy the challenge's
"not ChatGPT with search" and "must maintain a reusable knowledge base"
requirements. Code was written with AI coding assistance; every module was
tested (see inline test blocks and the manual verification performed while
building) before being treated as complete.

## 7. Known limitations / next steps
- Pipeline runs synchronously per topic (fine for a demo; a production
  version would use a background task queue for concurrent topics).
- No de-duplication of near-identical findings across sources yet.
- No authentication on the API (out of scope for the challenge).
