"""
query_executor.py — Safe database query execution.

Opens the SQLite database in READ-ONLY mode and executes validated queries.
This is the third safety layer — even if a destructive query somehow passes
validation, the read-only connection physically prevents any writes.
"""

import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sales_data.db")


def execute_query(sql_query, db_path=None):
    """
    Execute a validated SQL query against the database (read-only).
    
    Args:
        sql_query: The SQL SELECT query to run
        db_path: Path to the SQLite database file
    
    Returns:
        dict: {
            success: bool,
            data: list of dicts (each row as a dictionary),
            columns: list of column names,
            row_count: number of rows returned,
            error: str (only if success is False)
        }
    """
    db_path = db_path or DATABASE_PATH

    if not os.path.exists(db_path):
        return {
            "success": False,
            "error": "Database not found. Please run 'python backend/load_data.py' first.",
            "data": [],
            "columns": [],
            "row_count": 0
        }

    try:
        # SAFETY: Open database in read-only mode
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row  # Enables column name access
        cursor = conn.cursor()

        cursor.execute(sql_query)
        rows = cursor.fetchall()

        # Extract column names from the cursor
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Convert sqlite3.Row objects to plain dictionaries
        data = [dict(zip(columns, row)) for row in rows]

        conn.close()

        return {
            "success": True,
            "data": data,
            "columns": columns,
            "row_count": len(data)
        }

    except sqlite3.OperationalError as e:
        return {
            "success": False,
            "error": f"SQL execution error: {str(e)}",
            "data": [],
            "columns": [],
            "row_count": 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "data": [],
            "columns": [],
            "row_count": 0
        }


def get_table_info(db_path=None):
    """
    Retrieve metadata about the sales_data table:
    columns, row count, distinct values, date range.
    Used by the /api/schema endpoint and for Gemini context.
    """
    db_path = db_path or DATABASE_PATH

    if not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Column information
        cursor.execute("PRAGMA table_info(sales_data)")
        columns = [{"name": c[1], "type": c[2]} for c in cursor.fetchall()]

        # Row count
        cursor.execute("SELECT COUNT(*) FROM sales_data")
        row_count = cursor.fetchone()[0]

        # Distinct products
        cursor.execute("SELECT DISTINCT product FROM sales_data ORDER BY product")
        products = [r[0] for r in cursor.fetchall()]

        # Distinct categories
        cursor.execute("SELECT DISTINCT category FROM sales_data ORDER BY category")
        categories = [r[0] for r in cursor.fetchall()]

        # Distinct regions
        cursor.execute("SELECT DISTINCT region FROM sales_data ORDER BY region")
        regions = [r[0] for r in cursor.fetchall()]

        # Distinct sales channels
        cursor.execute("SELECT DISTINCT sales_channel FROM sales_data ORDER BY sales_channel")
        channels = [r[0] for r in cursor.fetchall()]

        # Distinct statuses
        cursor.execute("SELECT DISTINCT status FROM sales_data ORDER BY status")
        statuses = [r[0] for r in cursor.fetchall()]

        # Date range
        cursor.execute("SELECT MIN(order_date), MAX(order_date) FROM sales_data")
        date_range = cursor.fetchone()

        conn.close()

        return {
            "table_name": "sales_data",
            "columns": columns,
            "row_count": row_count,
            "products": products,
            "categories": categories,
            "regions": regions,
            "sales_channels": channels,
            "statuses": statuses,
            "date_range": {"min": date_range[0], "max": date_range[1]}
        }
    except Exception:
        return None
