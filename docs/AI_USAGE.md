# AI Tools Usage, Debugging, and Engineering Report

## 1. AI Tools Used

| Tool / Model | Role in Project | Justification |
|--------------|-----------------|---------------|
| **Google Gemini 2.0 Flash (`gemini-2.0-flash`)** | Core application LLM (runtime text-to-SQL + synthesis) | High generation speed (<1.5s), cost efficiency, native JSON schema mode, and strong relational SQL semantic parsing. |
| **Antigravity AI Pair Programmer** | Development assistant (architecture, implementation, testing) | Rapid scaffolding, automated testing, bug diagnosis, and project packaging. |

---

## 2. How AI Was Used During Development

1. **System & Security Architecture Design:**
   - Prompted to establish a 3-tier defense-in-depth model for database security (prompt guardrails -> AST/regex sanitizer -> OS-level read-only connection).
   - Designed a two-stage decoupled pipeline so that the LLM is never tasked with doing mental arithmetic or fabricating data.

2. **Schema Ingestion & ETL Implementation:**
   - Used AI to inspect the raw CSV dataset (`ai_bi_assistant_sales_data - GET.csv`) and identify real-world anomalies:
     - Row 34: `Quantity = 0`
     - Row 33: `Status = Returned`
     - Row 52: `Unit_price is empty` (TXN0051)
     - Non-standard date formats (`DD-MM-YYYY`)
   - Engineered data cleaning rules in `backend/load_data.py` to handle each anomaly cleanly without silent crashes.

3. **Prompt Engineering for Strict Grounding:**
   - Injected the explicit SQL schema and column definitions into the system prompt.
   - Constrained the model to output strict JSON schemas with `reasoning_steps`, `sql_query`, and `is_answerable`.
   - Set low model temperature (`0.1`) to ensure deterministic outputs.

4. **Test Suite Generation:**
   - Generated 34 comprehensive automated tests spanning SQL validation, ETL anomalies, benchmark queries, and edge cases (destructive injections, out-of-scope queries).

---

## 3. Problems Encountered During Development

### Problem 1: Windows Console Unicode Encoding Errors (`cp1252`)
- **Symptoms:** When executing `python backend/load_data.py` on Windows, Python crashed with:
  `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4ca' in position 2: character maps to <undefined>`.
- **Root Cause:** Windows PowerShell/cmd terminals default to standard Windows legacy code pages (`cp1252`), which cannot encode emoji characters (e.g. 📊, ✅, 📁) or unicode arrows (`→`).
- **Debugging & Resolution:**
  - Audited terminal stdout print statements across `load_data.py` and `app.py`.
  - Replaced unicode emojis and arrows with clean ASCII equivalents (`[DATA]`, `[OK]`, `[WARN]`, `->`, `-`).
  - Verified cross-platform compatibility across Windows, Linux, and macOS environments.

### Problem 2: Overly Restrictive Regex Trigger in Deterministic Fallback
- **Symptoms:** Automated test `test_ask_revenue_change_between_months` failed during initial pytest execution.
- **Root Cause:** The fallback matching logic required the exact substring `"month"` to be present in conjunction with `"change"`. However, natural user queries often say: *"How did revenue change between January and February?"* (naming the months directly without using the generic word "month").
- **Debugging & Resolution:**
  - Expanded the lexical matcher in `backend/gemini_service.py` to scan for calendar month names (`january`, `february`, etc.) alongside `"between"` and `"change"`.
  - Verified regex extraction parsed target months (`2026-01` and `2026-02`) and executed the correct delta calculation.

### Problem 3: Handling Missing Values (TXN0051) in Aggregations
- **Symptoms:** Initial SQL queries could have produced `NaN` or distorted averages if missing unit prices were coerced to `0`.
- **Root Cause:** Row TXN0051 had `Unit_price = ""`. Coercing this to `0` would falsely indicate a free transaction rather than unrecorded data.
- **Debugging & Resolution:**
  - Stored missing values as explicit SQL `NULL`.
  - Updated all analytical queries with `WHERE status = 'Completed' AND revenue IS NOT NULL`.
  - Verified `SUM(revenue)` correctly produced the accurate ground truth figure of **₹14,39,200.00**.

### Problem 4: Multi-Statement SQL Injection Risk
- **Symptoms:** A simple keyword check for `DROP` could potentially be bypassed if a user submitted: `SELECT * FROM sales_data; DROP TABLE sales_data`.
- **Root Cause:** SQLite allows multiple statements if semicolons are permitted.
- **Debugging & Resolution:**
  - Implemented explicit rejection of semicolons inside the query body in `backend/sql_validator.py`.
  - Added unit test `test_block_semicolon_chained_injection` to guarantee regression prevention.

---

## 4. What We Would Improve With Another Day of Work

1. **Natural Language Feedback Loop & Corrections:**
   - Allow users to say *"Wait, exclude online sales from that calculation"* to refine previous queries in conversational context.
2. **Dynamic Chart Visualizer Configuration:**
   - Allow users to toggle interactively between bar, line, and doughnut views directly on the UI for any tabular query result.
3. **Automated Query Explanation with EXPLAIN QUERY PLAN:**
   - Display SQLite's query execution plan alongside the SQL query to teach business users about database index usage and performance.
4. **Vector Embedding Layer for Fuzzy Product Search:**
   - Add a small SQLite-VSS or TF-IDF fuzzy matcher so typos like *"wireless mose"* or *"lptop stand"* automatically map to `"Wireless Mouse"` and `"Laptop Stand"`.
5. **CSV Upload UI:**
   - Provide a drag-and-drop file upload zone in the frontend to let users upload any arbitrary sales transaction CSV and automatically analyze new datasets on the fly.
