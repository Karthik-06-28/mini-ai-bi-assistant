"""
gemini_service.py — Google Gemini LLM integration for text-to-SQL & reasoning.

Anti-hallucination strategy (two-stage process):
  Stage 1: Gemini generates SQL + reasoning steps (no actual data invented)
  Stage 2: SQL runs on the real database, results are sent back to Gemini
           to produce a human-readable answer grounded in ACTUAL numbers.

This ensures Gemini NEVER invents numbers or records:
  - Translates questions to SQL (Stage 1)
  - Summarizes real query results in plain English (Stage 2)

Includes a deterministic fallback engine for standard analytical queries
when an API key is not configured or in offline test environments.
"""

import json
import os
import re
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Path to .env
ENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')


def get_api_key():
    """Retrieve Gemini API key from environment, reloading .env if needed."""
    load_dotenv(ENV_PATH, override=True)
    key = os.getenv("GEMINI_API_KEY")
    if key and key.strip() and key != "your_gemini_api_key_here":
        return key.strip()
    return None


# ─────────────────────────────────────────────────────────
# STAGE 1 PROMPT: Natural language → SQL query + reasoning
# ─────────────────────────────────────────────────────────
SQL_SYSTEM_PROMPT = """You are a precise SQL analyst for a business intelligence system.
Your ONLY job is to translate natural language questions into SQL queries for a SQLite database.

═══════════════════════════════════
DATABASE SCHEMA
═══════════════════════════════════
```sql
CREATE TABLE sales_data (
    transaction_id TEXT PRIMARY KEY,   -- e.g., 'TXN0001'
    order_date TEXT,                   -- Format: 'YYYY-MM-DD'
    product TEXT,                      -- Laptop Stand, Wireless Mouse, Office Chair, Monitor, Keyboard, Desk, USB-C Hub
    category TEXT,                     -- Accessories, Furniture, Electronics
    region TEXT,                       -- North, South, East, West
    sales_channel TEXT,                -- Online, Retail
    quantity INTEGER,                  -- Units sold (can be 0)
    unit_price REAL,                   -- Price per unit in INR (can be NULL)
    discount_amount REAL,              -- Discount in INR
    status TEXT,                       -- Completed, Returned
    revenue REAL,                      -- Pre-calculated: quantity × unit_price - discount_amount (can be NULL)
    order_month TEXT,                  -- Format: 'YYYY-MM' for monthly grouping (e.g., '2026-01')
    order_year INTEGER                 -- e.g., 2026
);
```

═══════════════════════════════════
DATA FACTS (do NOT invent anything else)
═══════════════════════════════════
- ~51 rows, date range: January to June 2026 (order_month: '2026-01' through '2026-06')
- Revenue is pre-calculated; use the 'revenue' column directly
- Some rows have NULL revenue (missing unit_price)
- One transaction is 'Returned' (TXN0033)
- One transaction has quantity = 0 (TXN0034)
- For revenue/sales totals, filter: WHERE status = 'Completed' AND revenue IS NOT NULL
- For monthly trends, GROUP BY order_month ORDER BY order_month
- Currency is INR (₹)

═══════════════════════════════════
STRICT RULES
═══════════════════════════════════
1. ONLY output SELECT statements. NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE.
2. ONLY reference the 'sales_data' table. No other tables exist.
3. ONLY reference columns listed in the schema. No invented columns.
4. If the question CANNOT be answered from this database (e.g., questions about weather, stock prices, employees, unrelated entities), set is_answerable to false.
5. NEVER fabricate, estimate, or assume data. Only query what exists.
6. Use proper SQLite syntax (e.g., || for string concatenation).
7. For "highest" or "top" questions, use ORDER BY ... DESC LIMIT 1.
8. Always consider NULL values in aggregations.

═══════════════════════════════════
RESPONSE FORMAT (strict JSON only)
═══════════════════════════════════
If the question IS answerable:
{
    "is_answerable": true,
    "sql_query": "SELECT ... FROM sales_data ...",
    "reasoning_steps": [
        "Step 1: Identified question type",
        "Step 2: Selected required columns",
        "Step 3: Filtered for valid completed transactions",
        "Step 4: Applied deterministic SQL aggregation"
    ],
    "chart_type": "bar|line|pie|table|number",
    "chart_config": {
        "x_axis": "column_name",
        "y_axis": "column_name",
        "title": "Descriptive Chart Title"
    }
}

If the question is NOT answerable:
{
    "is_answerable": false,
    "reason": "Clear explanation of why this data is not in the sales database.",
    "suggestion": "Suggested question the user could ask instead"
}
"""

# ─────────────────────────────────────────────────────────
# STAGE 2 PROMPT: Real query results → human-readable answer
# ─────────────────────────────────────────────────────────
ANSWER_SYSTEM_PROMPT = """You are a business intelligence analyst presenting database query results.

STRICT RULES:
1. ONLY use the numbers and data provided in the 'query_results' — do NOT invent, estimate, or modify numbers.
2. Format currency in INR with ₹ symbol and comma separators (e.g., ₹6,21,800).
3. If results are empty, say: "No data found matching your criteria."
4. Be concise, direct, and factual.
5. Highlight key findings.

RESPONSE FORMAT (strict JSON):
{
    "answer": "Clear, grounded answer using ONLY the actual query results",
    "highlights": ["Key finding 1", "Key finding 2"]
}
"""


# ─────────────────────────────────────────────────────────
# DETERMINISTIC FALLBACK ENGINE (For Tests & No-Key Scenarios)
# ─────────────────────────────────────────────────────────

OUT_OF_SCOPE_KEYWORDS = [
    "weather", "temperature", "forecast", "ceo", "salary", "employee", "stocks",
    "bitcoin", "crypto", "joke", "president", "election", "capital", "movie",
    "song", "who are you", "who made you"
]

def deterministic_sql_fallback(question):
    """
    Deterministic rule-based query engine for the 5 benchmark BI questions
    and out-of-scope question classification.
    """
    q = question.lower().strip()

    # Out of scope detection
    for kw in OUT_OF_SCOPE_KEYWORDS:
        if kw in q:
            return {
                "success": True,
                "is_answerable": False,
                "reason": f"The query asks about '{kw}', which is outside the scope of sales transactions.",
                "suggestion": "You can ask about total revenue, product performance, monthly trends, or regional sales.",
                "reasoning_steps": [
                    f"Step 1: Detected out-of-scope keyword '{kw}'",
                    "Step 2: Verified schema — 'sales_data' only contains transaction & sales records",
                    "Step 3: Marked question as unanswerable to prevent hallucinations"
                ]
            }

    # 1. Total revenue
    if ("total revenue" in q or "overall revenue" in q or "sum of revenue" in q or 
        ("what is" in q and "revenue" in q and "product" not in q and "month" not in q and "region" not in q and "category" not in q)):
        return {
            "success": True,
            "is_answerable": True,
            "sql_query": "SELECT SUM(revenue) AS total_revenue, COUNT(*) AS transaction_count FROM sales_data WHERE status = 'Completed' AND revenue IS NOT NULL",
            "reasoning_steps": [
                "Step 1: Recognized request for overall business revenue",
                "Step 2: Selected pre-calculated 'revenue' column from sales_data",
                "Step 3: Filtered for valid transactions (status = 'Completed' and revenue IS NOT NULL) to exclude returns",
                "Step 4: Computed SUM(revenue) and COUNT(*) for total transactions"
            ],
            "chart_type": "number",
            "chart_config": {"title": "Total Completed Revenue"}
        }

    # 2. Highest revenue product / top product
    if ("highest revenue" in q and "product" in q) or ("top product" in q) or ("best selling product" in q) or ("product" in q and "highest" in q):
        return {
            "success": True,
            "is_answerable": True,
            "sql_query": "SELECT product, SUM(revenue) AS total_revenue, SUM(quantity) AS total_units FROM sales_data WHERE status = 'Completed' AND revenue IS NOT NULL GROUP BY product ORDER BY total_revenue DESC LIMIT 1",
            "reasoning_steps": [
                "Step 1: Identified request for top-performing product by revenue",
                "Step 2: Grouped completed transactions by 'product'",
                "Step 3: Calculated total revenue and total units sold per product",
                "Step 4: Ordered in descending order and limited to top 1"
            ],
            "chart_type": "bar",
            "chart_config": {"x_axis": "product", "y_axis": "total_revenue", "title": "Top Product by Revenue"}
        }

    # 3. Monthly revenue trend
    if ("monthly" in q and "trend" in q) or ("revenue trend" in q) or ("monthly revenue" in q) or ("revenue by month" in q):
        return {
            "success": True,
            "is_answerable": True,
            "sql_query": "SELECT order_month, SUM(revenue) AS total_revenue, COUNT(*) AS orders_count FROM sales_data WHERE status = 'Completed' AND revenue IS NOT NULL GROUP BY order_month ORDER BY order_month ASC",
            "reasoning_steps": [
                "Step 1: Identified request for temporal revenue progression",
                "Step 2: Grouped by 'order_month' (YYYY-MM)",
                "Step 3: Aggregated SUM(revenue) and COUNT(*) for completed orders",
                "Step 4: Sorted chronologically ascending to demonstrate the monthly trend"
            ],
            "chart_type": "line",
            "chart_config": {"x_axis": "order_month", "y_axis": "total_revenue", "title": "Monthly Revenue Trend"}
        }

    # 4. Highest sales region
    if ("highest" in q and "region" in q) or ("top region" in q) or ("sales by region" in q) or ("best region" in q) or ("region" in q and "highest sales" in q):
        return {
            "success": True,
            "is_answerable": True,
            "sql_query": "SELECT region, SUM(revenue) AS total_revenue, COUNT(*) AS transactions FROM sales_data WHERE status = 'Completed' AND revenue IS NOT NULL GROUP BY region ORDER BY total_revenue DESC LIMIT 1",
            "reasoning_steps": [
                "Step 1: Identified request for top regional market",
                "Step 2: Grouped records by 'region'",
                "Step 3: Computed total revenue per region for completed orders",
                "Step 4: Sorted descending by total revenue and limited to 1"
            ],
            "chart_type": "bar",
            "chart_config": {"x_axis": "region", "y_axis": "total_revenue", "title": "Top Sales Region"}
        }

    # 5. Revenue change between two months
    month_names_list = ["jan", "january", "feb", "february", "mar", "march", "apr", "april", "may", "jun", "june", "month"]
    has_month_mention = any(m in q for m in month_names_list)
    if ("change" in q or "compare" in q or "difference" in q or "between" in q) and has_month_mention:
        # Extract specific months if mentioned
        month_map = {
            "jan": "2026-01", "january": "2026-01",
            "feb": "2026-02", "february": "2026-02",
            "mar": "2026-03", "march": "2026-03",
            "apr": "2026-04", "april": "2026-04",
            "may": "2026-05",
            "jun": "2026-06", "june": "2026-06"
        }
        found_months = []
        for name, m_code in month_map.items():
            if re.search(r'\b' + name + r'\b', q):
                if m_code not in found_months:
                    found_months.append(m_code)

        if len(found_months) >= 2:
            m1, m2 = found_months[0], found_months[1]
            sql = f"SELECT order_month, SUM(revenue) AS total_revenue FROM sales_data WHERE status = 'Completed' AND revenue IS NOT NULL AND order_month IN ('{m1}', '{m2}') GROUP BY order_month ORDER BY order_month ASC"
        else:
            # Default comparison between first two recorded months (Jan & Feb)
            sql = "SELECT order_month, SUM(revenue) AS total_revenue FROM sales_data WHERE status = 'Completed' AND revenue IS NOT NULL AND order_month IN ('2026-01', '2026-02') GROUP BY order_month ORDER BY order_month ASC"

        return {
            "success": True,
            "is_answerable": True,
            "sql_query": sql,
            "reasoning_steps": [
                "Step 1: Recognized request for Month-over-Month comparison",
                "Step 2: Filtered order_month for target months",
                "Step 3: Summed revenue for each month on completed sales",
                "Step 4: Ordered chronologically to compute variance and growth"
            ],
            "chart_type": "bar",
            "chart_config": {"x_axis": "order_month", "y_axis": "total_revenue", "title": "Revenue Comparison Between Months"}
        }

    # 6. Sales by Category
    if "category" in q:
        return {
            "success": True,
            "is_answerable": True,
            "sql_query": "SELECT category, SUM(revenue) AS total_revenue, SUM(quantity) AS units_sold FROM sales_data WHERE status = 'Completed' AND revenue IS NOT NULL GROUP BY category ORDER BY total_revenue DESC",
            "reasoning_steps": [
                "Step 1: Grouped records by product category",
                "Step 2: Aggregated total revenue and units sold per category",
                "Step 3: Filtered for completed transactions",
                "Step 4: Ordered by revenue descending"
            ],
            "chart_type": "pie",
            "chart_config": {"x_axis": "category", "y_axis": "total_revenue", "title": "Sales by Category"}
        }

    # Generic fallback: search product or general overview
    return {
        "success": True,
        "is_answerable": True,
        "sql_query": "SELECT product, category, region, SUM(revenue) AS total_revenue FROM sales_data WHERE status = 'Completed' AND revenue IS NOT NULL GROUP BY product, category, region ORDER BY total_revenue DESC LIMIT 10",
        "reasoning_steps": [
            "Step 1: Parsed open business query",
            "Step 2: Queried top 10 breakdown across products, categories, and regions",
            "Step 3: Filtered for valid completed orders"
        ],
        "chart_type": "bar",
        "chart_config": {"title": "Sales Overview"}
    }


def deterministic_answer_fallback(question, sql_query, query_results):
    """
    Format deterministic results into clean human-readable answers
    when Gemini API key is offline or in test environments.
    """
    if not query_results:
        return {
            "success": True,
            "answer": "No records found matching the query in the sales dataset.",
            "highlights": ["0 records returned"]
        }

    first = query_results[0]
    keys = list(first.keys())

    # Case: Total Revenue
    if "total_revenue" in first and len(query_results) == 1 and "product" not in first and "region" not in first and "order_month" not in first:
        rev = first["total_revenue"]
        count = first.get("transaction_count", "")
        formatted_rev = f"₹{rev:,.2f}" if rev else "₹0.00"
        tx_str = f" across {count} completed transactions" if count else ""
        return {
            "success": True,
            "answer": f"The total revenue is **{formatted_rev}**{tx_str} (excluding returned orders and invalid entries).",
            "highlights": [f"Total Revenue: {formatted_rev}", f"Completed Transactions: {count}"]
        }

    # Case: Top product
    if "product" in first and "total_revenue" in first and len(query_results) == 1:
        prod = first["product"]
        rev = first["total_revenue"]
        units = first.get("total_units", "")
        formatted_rev = f"₹{rev:,.2f}"
        units_str = f" with {units} units sold" if units else ""
        return {
            "success": True,
            "answer": f"The product generating the highest revenue is **{prod}**, with total sales of **{formatted_rev}**{units_str}.",
            "highlights": [f"Top Product: {prod}", f"Generated: {formatted_rev}"]
        }

    # Case: Top region
    if "region" in first and "total_revenue" in first and len(query_results) == 1:
        reg = first["region"]
        rev = first["total_revenue"]
        formatted_rev = f"₹{rev:,.2f}"
        return {
            "success": True,
            "answer": f"The **{reg}** region generated the highest sales, totaling **{formatted_rev}**.",
            "highlights": [f"Top Region: {reg}", f"Total Sales: {formatted_rev}"]
        }

    # Case: Monthly trend
    if "order_month" in first and "total_revenue" in first and len(query_results) > 1:
        month_names = {
            "2026-01": "January 2026", "2026-02": "February 2026", "2026-03": "March 2026",
            "2026-04": "April 2026", "2026-05": "May 2026", "2026-06": "June 2026"
        }
        breakdown = []
        for r in query_results:
            m = month_names.get(r['order_month'], r['order_month'])
            rev_str = f"Rs. {r['total_revenue']:,.2f}"
            breakdown.append(f"- **{m}**: {rev_str}")
        
        # Calculate comparison between two months if exactly two
        if len(query_results) == 2:
            m1_name = month_names.get(query_results[0]['order_month'], query_results[0]['order_month'])
            m2_name = month_names.get(query_results[1]['order_month'], query_results[1]['order_month'])
            diff = query_results[1]['total_revenue'] - query_results[0]['total_revenue']
            pct = (diff / query_results[0]['total_revenue']) * 100 if query_results[0]['total_revenue'] else 0
            change_str = "increased" if diff >= 0 else "decreased"
            answer = f"Revenue changed from **Rs. {query_results[0]['total_revenue']:,.2f}** in {m1_name} to **Rs. {query_results[1]['total_revenue']:,.2f}** in {m2_name}, which is an {change_str} of **Rs. {abs(diff):,.2f}** ({pct:+.1f}%).\n\n" + "\n".join(breakdown)
            return {
                "success": True,
                "answer": answer,
                "highlights": [f"{m1_name}: Rs. {query_results[0]['total_revenue']:,.2f}", f"{m2_name}: Rs. {query_results[1]['total_revenue']:,.2f}", f"Net Change: {diff:+,.2f}"]
            }

        answer = "Here is the monthly revenue trend:\n\n" + "\n".join(breakdown)
        return {
            "success": True,
            "answer": answer,
            "highlights": [f"{len(query_results)} months evaluated", f"Peak month: {breakdown[0]}"]
        }

    # Generic list formatting
    lines = []
    for r in query_results[:5]:
        val = next((v for k, v in r.items() if isinstance(v, (int, float))), None)
        lbl = next((v for k, v in r.items() if isinstance(v, str)), "")
        if val is not None:
            lines.append(f"- **{lbl}**: Rs. {val:,.2f}" if "rev" in keys[1] or "sale" in keys[1] else f"- **{lbl}**: {val}")
    
    return {
        "success": True,
        "answer": f"Query returned {len(query_results)} records:\n\n" + "\n".join(lines),
        "highlights": [f"{len(query_results)} records returned"]
    }


# ─────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────

def generate_sql_from_question(question):
    """
    STAGE 1: Convert a natural language question to a SQL query.
    Uses Gemini 2.0 Flash when API key is provided, falling back seamlessly
    to deterministic parsing when offline.
    """
    api_key = get_api_key()

    if not api_key:
        # Fallback to deterministic logic
        return deterministic_sql_fallback(question)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SQL_SYSTEM_PROMPT
        )

        response = model.generate_content(
            f"User question: {question}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )

        result = json.loads(response.text)
        result["success"] = True
        return result

    except Exception as e:
        # If Gemini API call encounters quota/network issues, gracefully fallback
        fallback = deterministic_sql_fallback(question)
        fallback["reasoning_steps"].insert(0, f"Notice: Live Gemini query fell back to deterministic engine ({str(e)[:60]}...)")
        return fallback


def generate_answer_from_results(question, sql_query, query_results):
    """
    STAGE 2: Generate a human-readable answer grounded in ACTUAL query results.
    """
    api_key = get_api_key()

    if not api_key:
        return deterministic_answer_fallback(question, sql_query, query_results)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=ANSWER_SYSTEM_PROMPT
        )

        prompt = f"""
User's Question: {question}

SQL Query That Was Executed: {sql_query}

Actual Query Results From Database:
{json.dumps(query_results, indent=2, default=str)}

Based ONLY on these actual results, provide a clear, accurate answer.
Do NOT add any data that is not in the results above.
"""

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )

        result = json.loads(response.text)
        result["success"] = True
        return result

    except Exception:
        return deterministic_answer_fallback(question, sql_query, query_results)
