"""
test_sql_validator.py — Automated tests for SQL safety and sanitization.

Verifies:
  1. Valid SELECT queries are approved.
  2. Destructive SQL operations (DROP, DELETE, UPDATE, INSERT) are blocked.
  3. Multi-statement injection attempts are blocked.
  4. SQL comments (used to obfuscate malicious SQL) are blocked.
  5. Queries targeting unauthorized tables are rejected.
"""

import pytest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.sql_validator import validate_sql, sanitize_sql


class TestSqlValidator:
    """Test suite for SQL safety validator."""

    def test_valid_simple_select(self):
        """Valid SELECT query should pass."""
        sql = "SELECT SUM(revenue) FROM sales_data WHERE status = 'Completed'"
        is_valid, msg = validate_sql(sql)
        assert is_valid is True
        assert "valid and safe" in msg

    def test_valid_aggregation_and_group_by(self):
        """Valid GROUP BY with ORDER BY should pass."""
        sql = "SELECT product, SUM(revenue) FROM sales_data GROUP BY product ORDER BY 2 DESC LIMIT 1"
        is_valid, msg = validate_sql(sql)
        assert is_valid is True

    def test_block_drop_table(self):
        """DROP TABLE must be strictly blocked."""
        sql = "DROP TABLE sales_data"
        is_valid, msg = validate_sql(sql)
        assert is_valid is False
        assert "Only SELECT queries are allowed" in msg or "Dangerous SQL keyword" in msg

    def test_block_delete_from(self):
        """DELETE statements must be blocked."""
        sql = "DELETE FROM sales_data WHERE status = 'Returned'"
        is_valid, msg = validate_sql(sql)
        assert is_valid is False

    def test_block_update_statement(self):
        """UPDATE statements must be blocked."""
        sql = "UPDATE sales_data SET revenue = 0"
        is_valid, msg = validate_sql(sql)
        assert is_valid is False

    def test_block_insert_statement(self):
        """INSERT statements must be blocked."""
        sql = "INSERT INTO sales_data (transaction_id) VALUES ('TXN9999')"
        is_valid, msg = validate_sql(sql)
        assert is_valid is False

    def test_block_semicolon_chained_injection(self):
        """Multiple statements chained with semicolons must be blocked."""
        sql = "SELECT * FROM sales_data; DROP TABLE sales_data"
        is_valid, msg = validate_sql(sql)
        assert is_valid is False
        assert "Multiple SQL statements" in msg or "Dangerous SQL keyword" in msg

    def test_block_sql_comments(self):
        """SQL comments (-- or /* */) must be blocked to prevent evasion."""
        sql = "SELECT * FROM sales_data -- ignore this"
        is_valid, msg = validate_sql(sql)
        assert is_valid is False
        assert "SQL comments are not allowed" in msg

    def test_block_unauthorized_table(self):
        """Accessing tables other than sales_data must be blocked."""
        sql = "SELECT * FROM users"
        is_valid, msg = validate_sql(sql)
        assert is_valid is False
        assert "Unknown table" in msg

    def test_block_empty_query(self):
        """Empty query strings must be rejected."""
        is_valid, msg = validate_sql("")
        assert is_valid is False

        is_valid, msg = validate_sql("   ")
        assert is_valid is False

    def test_sanitize_sql_trims_and_removes_semicolon(self):
        """Sanitizer should cleanly strip whitespace and trailing semicolons."""
        raw = "   SELECT * FROM sales_data;   "
        clean = sanitize_sql(raw)
        assert clean == "SELECT * FROM sales_data"
