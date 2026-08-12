"""
database.py
------------
Persistent research knowledge base (SQLite).

This is the layer that makes the app a real "research knowledge base"
rather than a stateless ChatGPT-with-search wrapper. Every topic ever
researched, every source fetched, every finding extracted, every
contradiction detected, and every conclusion generated is stored here
permanently -- restarting the app does not lose intelligence.

Schema:
  topics         one row per research question the user has ever asked
  sub_questions  the LLM-generated research plan for a topic
  sources        web pages found + fetched for a sub-question
  findings       atomic factual claims extracted from a source
  contradictions pairs of findings that conflict, with an explanation
  conclusions    final synthesized answers, each citing finding ids
"""

import sqlite3
import json
import datetime
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "research.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending | running | done | error
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS sub_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    text TEXT NOT NULL,
    category TEXT,
    order_index INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    sub_question_id INTEGER REFERENCES sub_questions(id),
    url TEXT NOT NULL,
    title TEXT,
    snippet TEXT,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    source_id INTEGER NOT NULL REFERENCES sources(id),
    text TEXT NOT NULL,
    category TEXT,             -- e.g. inventory, customer-experience, workforce, risk
    strength TEXT,              -- strong | moderate | weak (evidence strength)
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contradictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    finding_a_id INTEGER NOT NULL REFERENCES findings(id),
    finding_b_id INTEGER NOT NULL REFERENCES findings(id),
    explanation TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conclusions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    text TEXT NOT NULL,
    supporting_finding_ids TEXT NOT NULL,   -- JSON list of finding ids
    confidence TEXT,                        -- high | medium | low
    order_index INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------- topics ----------

def create_topic(question: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO topics (question, status, created_at) VALUES (?, 'pending', ?)",
            (question, now()),
        )
        return cur.lastrowid


def set_topic_status(topic_id: int, status: str):
    with get_conn() as conn:
        if status == "done":
            conn.execute(
                "UPDATE topics SET status = ?, completed_at = ? WHERE id = ?",
                (status, now(), topic_id),
            )
        else:
            conn.execute("UPDATE topics SET status = ? WHERE id = ?", (status, topic_id))


def get_topic(topic_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        return dict(row) if row else None


def list_topics():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM topics ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


# ---------- sub_questions ----------

def add_sub_question(topic_id: int, text: str, category: str, order_index: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO sub_questions (topic_id, text, category, order_index) VALUES (?, ?, ?, ?)",
            (topic_id, text, category, order_index),
        )
        return cur.lastrowid


def get_sub_questions(topic_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sub_questions WHERE topic_id = ? ORDER BY order_index", (topic_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- sources ----------

def add_source(topic_id: int, sub_question_id: int, url: str, title: str, snippet: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO sources (topic_id, sub_question_id, url, title, snippet, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (topic_id, sub_question_id, url, title, snippet, now()),
        )
        return cur.lastrowid


def get_sources(topic_id: int):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM sources WHERE topic_id = ?", (topic_id,)).fetchall()
        return [dict(r) for r in rows]


def get_source(source_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        return dict(row) if row else None


# ---------- findings ----------

def add_finding(topic_id: int, source_id: int, text: str, category: str, strength: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO findings (topic_id, source_id, text, category, strength, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (topic_id, source_id, text, category, strength, now()),
        )
        return cur.lastrowid


def get_findings(topic_id: int, category: str = None):
    with get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM findings WHERE topic_id = ? AND category = ?",
                (topic_id, category),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM findings WHERE topic_id = ?", (topic_id,)).fetchall()
        return [dict(r) for r in rows]


def get_findings_by_ids(finding_ids):
    if not finding_ids:
        return []
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in finding_ids)
        rows = conn.execute(
            f"SELECT * FROM findings WHERE id IN ({placeholders})", finding_ids
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- contradictions ----------

def add_contradiction(topic_id: int, finding_a_id: int, finding_b_id: int, explanation: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO contradictions (topic_id, finding_a_id, finding_b_id, explanation, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (topic_id, finding_a_id, finding_b_id, explanation, now()),
        )
        return cur.lastrowid


def get_contradictions(topic_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM contradictions WHERE topic_id = ?", (topic_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- conclusions ----------

def add_conclusion(topic_id: int, text: str, supporting_finding_ids, confidence: str, order_index: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO conclusions (topic_id, text, supporting_finding_ids, confidence, order_index, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (topic_id, text, json.dumps(supporting_finding_ids), confidence, order_index, now()),
        )
        return cur.lastrowid


def get_conclusions(topic_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM conclusions WHERE topic_id = ? ORDER BY order_index", (topic_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["supporting_finding_ids"] = json.loads(d["supporting_finding_ids"])
            out.append(d)
        return out


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
