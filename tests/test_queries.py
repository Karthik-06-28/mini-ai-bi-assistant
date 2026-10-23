"""
test_queries.py — Automated tests for the 5 benchmark Business Intelligence questions.

Problem Statement questions:
  1. What is the total revenue?
  2. Which product generated the highest revenue?
  3. What is the monthly revenue trend?
  4. Which region generated the highest sales?
  5. How did revenue change between two months?

Verifies:
  - Queries return deterministic results.
  - Calculations accurately use SQL and exclude returns and nulls where appropriate.
  - Numbers match verified ground truth from the CSV.
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.query_executor import execute_query
from backend.load_data import load_csv_to_database
from backend.config import CSV_PATH


class TestBenchmarkQueries:
    """Test suite executing the 5 core business questions against real data."""

    @pytest.fixture(scope="class", autouse=True)
    def setup_database(self, tmp_path_factory):
        """Ensure test database is primed."""
        temp_dir = tmp_path_factory.mktemp("query_test_db")
        self.__class__.db_path = os.path.join(temp_dir, "query_sales.db")
        load_csv_to_database(csv_path=CSV_PATH, db_path=self.__class__.db_path)

    def test_q1_total_revenue(self):
        """Question 1: What is the total revenue?"""
        sql = """
            SELECT SUM(revenue) AS total_revenue, COUNT(*) AS completed_count
            FROM sales_data
            WHERE status = 'Completed' AND revenue IS NOT NULL
        """
        res = execute_query(sql, db_path=self.db_path)
        assert res["success"] is True
        assert len(res["data"]) == 1
        total_rev = res["data"][0]["total_revenue"]
        # Ground truth: 1,439,200.00
        assert total_rev == 1439200.0
        assert res["data"][0]["completed_count"] == 49

    def test_q2_highest_revenue_product(self):
        """Question 2: Which product generated the highest revenue?"""
        sql = """
            SELECT product, SUM(revenue) AS total_revenue
            FROM sales_data
            WHERE status = 'Completed' AND revenue IS NOT NULL
            GROUP BY product
            ORDER BY total_revenue DESC
            LIMIT 1
        """
        res = execute_query(sql, db_path=self.db_path)
        assert res["success"] is True
        assert len(res["data"]) == 1
        top_product = res["data"][0]["product"]
        top_rev = res["data"][0]["total_revenue"]
        # Ground truth: Monitor (473,000.00)
        assert top_product == "Monitor"
        assert top_rev == 473000.0

    def test_q3_monthly_revenue_trend(self):
        """Question 3: What is the monthly revenue trend?"""
        sql = """
            SELECT order_month, SUM(revenue) AS total_revenue
            FROM sales_data
            WHERE status = 'Completed' AND revenue IS NOT NULL
            GROUP BY order_month
            ORDER BY order_month ASC
        """
        res = execute_query(sql, db_path=self.db_path)
        assert res["success"] is True
        assert len(res["data"]) == 6  # 6 months (Jan - Jun 2026)
        
        # Verify chronological ordering
        months = [row["order_month"] for row in res["data"]]
        assert months == ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]

        # Verify month values
        rev_by_month = {row["order_month"]: row["total_revenue"] for row in res["data"]}
        assert rev_by_month["2026-01"] == 210250.0
        assert rev_by_month["2026-05"] == 318500.0  # Peak month

    def test_q4_highest_sales_region(self):
        """Question 4: Which region generated the highest sales?"""
        sql = """
            SELECT region, SUM(revenue) AS total_revenue
            FROM sales_data
            WHERE status = 'Completed' AND revenue IS NOT NULL
            GROUP BY region
            ORDER BY total_revenue DESC
            LIMIT 1
        """
        res = execute_query(sql, db_path=self.db_path)
        assert res["success"] is True
        assert len(res["data"]) == 1
        top_region = res["data"][0]["region"]
        top_rev = res["data"][0]["total_revenue"]
        # Ground truth: South (411,200.00)
        assert top_region == "South"
        assert top_rev == 411200.0

    def test_q5_revenue_change_between_two_months(self):
        """Question 5: How did revenue change between two months (Jan and Feb 2026)?"""
        sql = """
            SELECT order_month, SUM(revenue) AS total_revenue
            FROM sales_data
            WHERE status = 'Completed' AND revenue IS NOT NULL AND order_month IN ('2026-01', '2026-02')
            GROUP BY order_month
            ORDER BY order_month ASC
        """
        res = execute_query(sql, db_path=self.db_path)
        assert res["success"] is True
        assert len(res["data"]) == 2
        
        jan_rev = res["data"][0]["total_revenue"]
        feb_rev = res["data"][1]["total_revenue"]
        delta = feb_rev - jan_rev
        pct_change = (delta / jan_rev) * 100

        assert jan_rev == 210250.0
        assert feb_rev == 234600.0
        assert delta == 24350.0  # Revenue increased by 24,350
        assert round(pct_change, 2) == 11.58
