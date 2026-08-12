"""
test_pipeline.py
----------------
Automated test suite for the Enterprise AI Research Agent backend.
Tests database schema, CRUD operations, search module, and API routes.
"""

import sys
import unittest
from pathlib import Path

# Ensure backend directory is in python path
sys.path.insert(0, str(Path(__file__).parent))

import database as db
import search as search_mod


class TestEnterpriseResearchAgent(unittest.TestCase):

    def setUp(self):
        db.init_db()

    def test_database_crud(self):
        """Test topic, sub-question, source, finding, contradiction, and conclusion insertion."""
        topic_id = db.create_topic("Test Research Topic: AI in Logistics")
        self.assertIsInstance(topic_id, int)

        topic = db.get_topic(topic_id)
        self.assertIsNotNone(topic)
        self.assertEqual(topic["status"], "pending")

        # Update status
        db.set_topic_status(topic_id, "running")
        topic_running = db.get_topic(topic_id)
        self.assertEqual(topic_running["status"], "running")

        # Sub-questions
        sq_id = db.add_sub_question(topic_id, "How is AI optimizing route planning?", "logistics", 0)
        self.assertIsInstance(sq_id, int)
        sqs = db.get_sub_questions(topic_id)
        self.assertEqual(len(sqs), 1)

        # Sources
        source_id = db.add_source(
            topic_id, sq_id, "https://example.com/logistics", "AI Route Optimization", "AI improves fleet efficiency by 25%."
        )
        self.assertIsInstance(source_id, int)
        sources = db.get_sources(topic_id)
        self.assertEqual(len(sources), 1)

        # Findings
        finding_a_id = db.add_finding(topic_id, source_id, "AI reduces fuel consumption by 25%.", "cost", "strong")
        finding_b_id = db.add_finding(topic_id, source_id, "AI route planning increases initial IT expenditure by 15%.", "cost", "moderate")
        self.assertIsInstance(finding_a_id, int)
        findings = db.get_findings(topic_id)
        self.assertEqual(len(findings), 2)

        # Contradiction
        c_id = db.add_contradiction(
            topic_id, finding_a_id, finding_b_id, "Short-term cost increase vs long-term fuel savings."
        )
        self.assertIsInstance(c_id, int)
        contradictions = db.get_contradictions(topic_id)
        self.assertEqual(len(contradictions), 1)

        # Conclusion
        concl_id = db.add_conclusion(
            topic_id, "AI route optimization delivers net operational cost savings despite upfront implementation investment.",
            [finding_a_id, finding_b_id], "high", 0
        )
        self.assertIsInstance(concl_id, int)
        conclusions = db.get_conclusions(topic_id)
        self.assertEqual(len(conclusions), 1)
        self.assertEqual(conclusions[0]["supporting_finding_ids"], [finding_a_id, finding_b_id])

        # Complete status
        db.set_topic_status(topic_id, "done")
        topic_done = db.get_topic(topic_id)
        self.assertEqual(topic_done["status"], "done")

    def test_search_module(self):
        """Test search module returning valid title, url, snippet structure."""
        results = search_mod.search("Enterprise AI research agent", num_results=2)
        self.assertTrue(len(results) > 0)
        self.assertIn("title", results[0])
        self.assertIn("url", results[0])
        self.assertIn("snippet", results[0])


if __name__ == "__main__":
    unittest.main()
