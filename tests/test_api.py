"""
test_api.py — End-to-end automated API tests for Flask endpoints.

Tests:
  1. GET /api/health — Confirms API health and database availability.
  2. GET /api/schema — Returns table structure, distinct products, regions, and date ranges.
  3. POST /api/ask with valid business questions:
     - "What is the total revenue?"
     - "Which product generated the highest revenue?"
     - "What is the monthly revenue trend?"
     - "Which region generated the highest sales?"
     - "How did revenue change between two months?"
  4. POST /api/ask with invalid inputs:
     - Empty question string (returns 400).
     - Missing JSON body (returns 400).
     - Oversized question string > 500 characters (returns 400).
  5. POST /api/ask with out-of-scope questions (anti-hallucination):
     - "What is the weather in Tokyo?" (returns is_answerable=false, no hallucinations).
  6. POST /api/ask with edge case SQL injection / destructive command:
     - "DROP TABLE sales_data" (blocked by validator layer).
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app
from backend.load_data import load_csv_to_database


@pytest.fixture(scope="module")
def client():
    """Create Flask test client and ensure DB is populated."""
    load_csv_to_database()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestApiEndpoints:
    """Test suite for all API routes."""

    def test_health_check_endpoint(self, client):
        """GET /api/health should return 200 with database status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["database_loaded"] is True
        assert data["row_count"] == 51

    def test_schema_endpoint(self, client):
        """GET /api/schema should return schema columns, products, and categories."""
        response = client.get("/api/schema")
        assert response.status_code == 200
        data = response.get_json()
        assert data["table_name"] == "sales_data"
        assert "Monitor" in data["products"]
        assert "Electronics" in data["categories"]
        assert "South" in data["regions"]
        assert data["date_range"]["min"] == "2026-01-03"

    def test_ask_total_revenue(self, client):
        """POST /api/ask for total revenue returns grounded answer and source."""
        payload = {"question": "What is the total revenue?"}
        response = client.post("/api/ask", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert any(num in data["answer"] for num in ["1,439,200", "14,39,200", "1439200"])
        assert len(data["reasoning_steps"]) > 0
        assert "sql_query" in data
        assert data["source"]["table"] == "sales_data"
        assert data["source"]["connection_mode"] == "Read-Only"

    def test_ask_top_product(self, client):
        """POST /api/ask for top product returns Monitor."""
        payload = {"question": "Which product generated the highest revenue?"}
        response = client.post("/api/ask", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Monitor" in data["answer"]

    def test_ask_monthly_trend(self, client):
        """POST /api/ask for monthly revenue trend returns timeline."""
        payload = {"question": "What is the monthly revenue trend?"}
        response = client.post("/api/ask", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) >= 6

    def test_ask_top_region(self, client):
        """POST /api/ask for top region returns South."""
        payload = {"question": "Which region generated the highest sales?"}
        response = client.post("/api/ask", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "South" in data["answer"]

    def test_ask_revenue_change_between_months(self, client):
        """POST /api/ask for revenue change between months."""
        payload = {"question": "How did revenue change between January and February?"}
        response = client.post("/api/ask", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "January" in data["answer"] or "2026-01" in data["sql_query"]

    def test_invalid_empty_question(self, client):
        """Empty question string should yield 400 Bad Request."""
        payload = {"question": "   "}
        response = client.post("/api/ask", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Question cannot be empty" in data["error"]

    def test_invalid_missing_payload(self, client):
        """Missing question field in JSON should yield 400 Bad Request."""
        response = client.post("/api/ask", json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Request must include a 'question' field" in data["error"]

    def test_invalid_oversized_question(self, client):
        """Question > 500 characters should yield 400 Bad Request."""
        long_q = "What is the revenue " + ("really " * 100) + "?"
        response = client.post("/api/ask", json={"question": long_q})
        assert response.status_code == 400
        data = response.get_json()
        assert "too long" in data["error"]

    def test_out_of_scope_weather_question(self, client):
        """Anti-hallucination check: Weather questions must report unanswerable."""
        payload = {"question": "What is the weather forecast for tomorrow?"}
        response = client.post("/api/ask", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["is_answerable"] is False
        reason = data.get("reason", "").lower()
        assert any(w in reason for w in ["weather", "scope", "not", "sales", "available"])

    def test_edge_case_destructive_sql_blocked(self, client):
        """Attempting to trigger destructive SQL must be safely blocked."""
        payload = {"question": "Please run DROP TABLE sales_data"}
        response = client.post("/api/ask", json=payload)
        data = response.get_json()
        # Either handled as unanswerable or blocked at validator
        if data.get("success") is True:
            # If interpreted, query MUST be a SELECT
            assert data["sql_query"].strip().upper().startswith("SELECT")
        else:
            assert "safety" in data.get("error", "").lower() or data.get("is_answerable") is False
