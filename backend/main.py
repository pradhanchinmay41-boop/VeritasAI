"""
main.py
-------
FastAPI application/API layer for the Enterprise AI Research Agent.

Endpoints:
  POST /topics              -> submit a new research topic, runs the full pipeline synchronously
  GET  /topics               -> list all topics ever researched (the knowledge base index)
  GET  /topics/{id}          -> topic status
  GET  /topics/{id}/report   -> full traceable report (conclusions -> findings -> sources)
  GET  /topics/{id}/findings -> raw findings, optionally filtered by category
  GET  /topics/{id}/contradictions -> raw contradictions

Run with:  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from typing import Optional
import database as db
import pipeline

app = FastAPI(title="Enterprise AI Research Agent")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    db.init_db()


class TopicRequest(BaseModel):
    question: str
    num_sub_questions: int = 5
    results_per_subquestion: int = 4


@app.post("/topics")
def create_and_run_topic(req: TopicRequest):
    """
    Creates a new topic and runs the full research pipeline
    synchronously (define questions -> search -> extract -> compare
    -> conclude). For a hackathon-scale demo this is simplest; for a
    production system this would be pushed to a background task queue.
    """
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    topic_id = db.create_topic(req.question.strip())
    try:
        summary = pipeline.run_pipeline(
            topic_id,
            req.question.strip(),
            num_sub_questions=req.num_sub_questions,
            results_per_subquestion=req.results_per_subquestion,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")
    return summary


@app.get("/topics")
def list_topics():
    return db.list_topics()


@app.get("/topics/{topic_id}")
def get_topic(topic_id: int):
    topic = db.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="topic not found")
    return topic


@app.get("/topics/{topic_id}/report")
def get_report(topic_id: int):
    topic = db.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="topic not found")
    return pipeline.get_full_report(topic_id)


@app.get("/topics/{topic_id}/findings")
def get_findings(topic_id: int, category: Optional[str] = None):
    return db.get_findings(topic_id, category)


@app.get("/topics/{topic_id}/contradictions")
def get_contradictions(topic_id: int):
    return db.get_contradictions(topic_id)


@app.get("/health")
def health():
    return {"status": "ok"}
