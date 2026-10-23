"""
test_loader.py — Automated tests for CSV loading, data cleaning, and handling edge cases.

Verifies:
  1. CSV is correctly loaded into SQLite.
  2. Missing unit_price (e.g., TXN0051) is handled gracefully as NULL.
  3. Zero quantity records (TXN0034) are properly parsed.
  4. Returned status orders (TXN0033) are preserved with status='Returned'.
  5. Revenue formula ((quantity * unit_price) - discount_amount) is computed accurately.
"""

import pytest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.load_data import load_csv_to_database
from backend.config import CSV_PATH


class TestDataLoader:
    """Test suite for CSV loading and cleaning operations."""

    @pytest.fixture(scope="class")
    def loaded_db(self, tmp_path_factory):
        """Load data into a temporary SQLite database for test isolation."""
        temp_dir = tmp_path_factory.mktemp("test_db")
        db_path = os.path.join(temp_dir, "test_sales.db")
        result = load_csv_to_database(csv_path=CSV_PATH, db_path=db_path)
        return {"db_path": db_path, "summary": result}

    def test_load_summary_counts(self, loaded_db):
        """Should successfully load all 51 rows with 1 cleaned record."""
        summary = loaded_db["summary"]
        assert summary["success"] is True
        assert summary["loaded"] == 51
        assert summary["cleaned"] >= 1
        assert summary["skipped"] == 0

    def test_missing_unit_price_edge_case(self, loaded_db):
        """Row TXN0051 had a missing unit_price. Must be stored as NULL and revenue NULL."""
        conn = sqlite3.connect(loaded_db["db_path"])
        cursor = conn.cursor()
        cursor.execute("SELECT unit_price, revenue FROM sales_data WHERE transaction_id = 'TXN0051'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] is None  # unit_price is NULL
        assert row[1] is None  # revenue is NULL

    def test_zero_quantity_edge_case(self, loaded_db):
        """Row TXN0034 had Quantity=0. Must have revenue = 0."""
        conn = sqlite3.connect(loaded_db["db_path"])
        cursor = conn.cursor()
        cursor.execute("SELECT quantity, unit_price, discount_amount, revenue FROM sales_data WHERE transaction_id = 'TXN0034'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == 0
        assert row[3] == 0.0

    def test_returned_status_preserved(self, loaded_db):
        """Row TXN0033 has Status='Returned'. Must be recorded as Returned."""
        conn = sqlite3.connect(loaded_db["db_path"])
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM sales_data WHERE transaction_id = 'TXN0033'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == 'Returned'

    def test_revenue_calculation_accuracy(self, loaded_db):
        """TXN0004: 6 units @ 9500 with 500 discount -> Revenue should be 56,500."""
        conn = sqlite3.connect(loaded_db["db_path"])
        cursor = conn.cursor()
        cursor.execute("SELECT quantity, unit_price, discount_amount, revenue FROM sales_data WHERE transaction_id = 'TXN0004'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        expected_revenue = (6 * 9500) - 500
        assert row[3] == expected_revenue
        assert row[3] == 56500.0

    def test_order_month_formatting(self, loaded_db):
        """Dates like 03-01-2026 should be normalized to order_month='2026-01'."""
        conn = sqlite3.connect(loaded_db["db_path"])
        cursor = conn.cursor()
        cursor.execute("SELECT order_date, order_month, order_year FROM sales_data WHERE transaction_id = 'TXN0001'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "2026-01-03"
        assert row[1] == "2026-01"
        assert row[2] == 2026
