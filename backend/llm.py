"""
llm.py
------
All LLM calls for the research pipeline, using Groq (free tier,
LLaMA-3.3-70B) via direct API calls / LangChain abstraction.

DESIGN NOTE (important for the "not one giant prompt" requirement):
Each pipeline stage below is a SEPARATE, narrowly-scoped LLM call with
its own prompt and its own strict JSON output schema. This is the
opposite of stuffing "do all the research and give me conclusions"
into a single prompt -- each stage only sees the specific inputs it
needs and only produces the specific structured output that stage is
responsible for. The orchestration (pipeline.py) is what chains them
together and writes each stage's output to the database before the
next stage runs.
"""

import os
import json
import re
import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

MODEL_NAME = "llama-3.3-70b-versatile"


def invoke_llm(prompt: str, temperature: float = 0.2) -> str:
    """
    Invokes LLM (Groq LLaMA-3.3-70B by default) via direct API call,
    falling back to Gemini or OpenAI if configured.
    """
    groq_key = os.environ.get("GROQ_API_KEY", "").strip().strip("'\"")
    if groq_key and groq_key != "your_groq_api_key_here":
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=40)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise RuntimeError(f"Groq API Error ({resp.status_code}): {resp.text}")

    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        resp = requests.post(url, json=payload, timeout=40)
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=40)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]

    raise RuntimeError(
        "GROQ_API_KEY is not set in environment or .env file. "
        "Get a free key at https://console.groq.com and set GROQ_API_KEY=... in your .env file."
    )


def _extract_json(raw: str):
    """
    LLMs sometimes wrap JSON in markdown fences or add stray text.
    Pull out the first {...} or [...] block and parse it.
    """
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\[.*\]|\{.*\})", raw, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"Could not parse JSON from LLM output:\n{raw}")


# ---------- Stage 1: Define Research Questions ----------

def generate_sub_questions(topic: str, n: int = 5) -> list[dict]:
    """
    Break a broad research topic into n focused sub-questions, each
    tagged with a category. This is the "research plan" stage.
    """
    prompt = f"""You are a research analyst planning an investigation into the following topic:

"{topic}"

Break this into exactly {n} focused, distinct sub-questions that together give thorough
coverage of the topic (e.g. different functional areas, stakeholder groups, or angles).
Each sub-question should be specific enough to search the web for directly.

Respond with ONLY a JSON array, no other text, in this exact format:
[
  {{"question": "...", "category": "short-category-label"}},
  ...
]"""
    resp_text = invoke_llm(prompt)
    return _extract_json(resp_text)


# ---------- Stage 2: Extract Findings ----------

def extract_findings(sub_question: str, source_title: str, source_snippet: str) -> list[dict]:
    """
    Given a single search result (title + snippet), extract discrete,
    atomic factual claims relevant to the sub-question. Each finding
    is tagged with a category and an evidence-strength label.
    """
    prompt = f"""You are extracting factual claims from a single web search result to answer this research sub-question:

Sub-question: "{sub_question}"

Source title: "{source_title}"
Source snippet: "{source_snippet}"

Extract up to 3 distinct, atomic factual claims from this snippet that are relevant to the
sub-question. Only extract claims that are actually supported by the snippet text -- do not
invent information beyond what's given. If the snippet contains no relevant factual claims,
return an empty array.

For each claim, classify:
- category: a short label for the theme (e.g. "inventory", "customer-experience", "workforce", "risk", "cost")
- strength: "strong" (specific data/study cited), "moderate" (clear claim, no specifics), or "weak" (vague/speculative)

Respond with ONLY a JSON array, no other text, in this exact format:
[
  {{"text": "...", "category": "...", "strength": "strong|moderate|weak"}},
  ...
]"""
    resp_text = invoke_llm(prompt)
    return _extract_json(resp_text)


# ---------- Stage 3: Detect Contradictions ----------

def detect_contradictions(findings: list[dict]) -> list[dict]:
    """
    Given a list of findings (each with id + text) within the same
    category, identify pairs that genuinely conflict and explain why.
    findings: [{"id": int, "text": str}, ...]
    """
    if len(findings) < 2:
        return []

    findings_block = "\n".join(f'- id={f["id"]}: "{f["text"]}"' for f in findings)
    prompt = f"""You are comparing research findings on the same theme to detect genuine contradictions
(not just different topics -- actual disagreement about the same fact or trend).

Findings:
{findings_block}

Identify pairs of findings above that contradict each other. Be conservative -- only flag a
pair if they genuinely disagree, not merely if they discuss different aspects. If there are no
real contradictions, return an empty array.

Respond with ONLY a JSON array, no other text, in this exact format:
[
  {{"finding_a_id": <id>, "finding_b_id": <id>, "explanation": "why these conflict"}},
  ...
]"""
    resp_text = invoke_llm(prompt)
    return _extract_json(resp_text)


# ---------- Stage 4: Generate Conclusions ----------

def generate_conclusions(topic: str, findings: list[dict], contradictions: list[dict]) -> list[dict]:
    """
    Synthesize the full set of findings (across all categories) into a
    small set of topic-level conclusions. Each conclusion MUST cite
    the specific finding ids that support it -- this is what gives the
    final output traceability back to evidence and sources.
    findings: [{"id": int, "text": str, "category": str}, ...]
    """
    findings_block = "\n".join(
        f'- id={f["id"]} [{f["category"]}]: "{f["text"]}"' for f in findings
    )
    contradictions_block = (
        "\n".join(
            f'- finding {c["finding_a_id"]} conflicts with finding {c["finding_b_id"]}: {c["explanation"]}'
            for c in contradictions
        )
        or "(none detected)"
    )

    prompt = f"""You are synthesizing a research investigation into a set of clear conclusions.

Research topic: "{topic}"

All findings gathered:
{findings_block}

Known contradictions among findings:
{contradictions_block}

Write 4-6 topic-level conclusions that synthesize these findings. Each conclusion MUST:
- be a single clear, specific statement (not vague)
- cite the exact finding ids (from the list above) that support it
- have a confidence level: "high" (multiple strong/moderate findings agree), "medium"
  (some support, possibly limited or with a noted contradiction), or "low" (thin or
  conflicting evidence)
- if a conclusion touches a topic with a known contradiction, note the disagreement explicitly
  in the conclusion text rather than ignoring it

Respond with ONLY a JSON array, no other text, in this exact format:
[
  {{"text": "...", "supporting_finding_ids": [<id>, <id>, ...], "confidence": "high|medium|low"}},
  ...
]"""
    resp_text = invoke_llm(prompt)
    return _extract_json(resp_text)


if __name__ == "__main__":
    # quick test
    print("llm.py loaded successfully.")
