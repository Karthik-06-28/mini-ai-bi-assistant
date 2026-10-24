# AI Tools Usage, Debugging, and Engineering Report

## 1. AI Tools Used

| Tool / Model | Role in Project | Justification |
|--------------|-----------------|---------------|
| **Google Gemini 3.5 Flash Lite (`gemini-3.5-flash-lite`)** | Core application LLM (runtime text-to-SQL + synthesis) | Low latency, cost efficiency, structured JSON output, and strong relational SQL semantic parsing. |
| **Antigravity AI Pair Programmer** | Development assistant (architecture, implementation, testing) | Rapid scaffolding, automated testing, bug diagnosis, and project packaging. |

---

## 2. How AI Was Used During Development

1. **System & Security Architecture Design**
   - Prompted to establish a 3-tier defense-in-depth model for database security (prompt guardrails -> regex sanitizer -> physical read-only connection).
   - Designed a decoupled pipeline so the LLM is never tasked with mental arithmetic or fabricating data.

2. **Schema Ingestion & ETL Implementation**
   - Used AI to inspect the raw CSV dataset (`ai_bi_assistant_sales_data - GET.csv`) and identify real-world anomalies:
     - Row 34: `Quantity = 0`
     - Row 33: `Status = Returned`
     - Row 52: `Unit_price` is empty (TXN0051)
     - Non-standard date format (`DD-MM-YYYY`)
   - Engineered data cleaning rules in `backend/load_data.py` to handle each anomaly without silent crashes.

3. **Prompt Engineering for Strict Grounding**
   - Injected the explicit SQL schema and column definitions into the system prompt.
   - Constrained the model to output strict JSON with `reasoning_steps`, `sql_query`, and `is_answerable`.
   - Set a low model temperature (`0.1`) for consistent outputs.

4. **Test Suite Generation**
   - Generated 34 automated tests spanning SQL validation, ETL anomalies, benchmark queries, and edge cases (destructive injections, out-of-scope queries).

---

## 3. Problems Encountered During Development

### Problem 1: Windows Console Unicode Encoding Errors (`cp1252`)
- **Symptoms:** Running `python backend/load_data.py` on Windows crashed with
  `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4ca' in position 2: character maps to <undefined>`.
- **Root Cause:** Windows PowerShell/cmd terminals default to legacy code pages (`cp1252`), which cannot encode emoji (e.g. 📊, ✅, 📁) or unicode arrows (`→`).
- **Resolution:**
  - Audited terminal print statements in `load_data.py` and `app.py`.
  - Replaced emoji and arrows with ASCII equivalents (`[DATA]`, `[OK]`, `[WARN]`, `->`, `-`).
  - Verified the output works across Windows, Linux, and macOS terminals.

### Problem 2: Overly Restrictive Matching in the Deterministic Fallback
- **Symptoms:** The automated test `test_ask_revenue_change_between_months` failed during the first pytest run.
- **Root Cause:** The fallback matcher required the literal word `"month"` alongside `"change"`. Natural queries often name the months directly, e.g. *"How did revenue change between January and February?"*
- **Resolution:**
  - Expanded the matcher in `backend/gemini_service.py` to detect calendar month names (`january`, `february`, etc.) alongside `"between"` and `"change"`.
  - Confirmed the target months (`2026-01` and `2026-02`) are extracted and the correct delta calculation runs.

### Problem 3: Handling Missing Values (TXN0051) in Aggregations
- **Symptoms:** Coercing the missing unit price to `0` could distort averages and aggregates.
- **Root Cause:** Row TXN0051 had `Unit_price = ""`. Treating it as `0` would falsely imply a free transaction rather than unrecorded data.
- **Resolution:**
  - Stored the missing value as an explicit SQL `NULL`.
  - Updated analytical queries to use `WHERE status = 'Completed' AND revenue IS NOT NULL`.
  - Verified `SUM(revenue)` produces the ground-truth total of **₹14,39,200.00**.

### Problem 4: Multi-Statement SQL Injection Risk
- **Symptoms:** A simple keyword check for `DROP` could be bypassed by input such as `SELECT * FROM sales_data; DROP TABLE sales_data`.
- **Root Cause:** SQLite allows multiple statements when semicolons are permitted.
- **Resolution:**
  - Rejected semicolons in the query body in `backend/sql_validator.py`.
  - Added the regression test `test_block_semicolon_chained_injection`.

---

## 4. Future Improvements

1. **Conversational Refinement:** Let users follow up with corrections such as *"Exclude online sales from that calculation"* using prior context.
2. **Dynamic Chart Controls:** Allow toggling between bar, line, and doughnut views for any tabular result.
3. **Query Plan Display:** Show SQLite's `EXPLAIN QUERY PLAN` output alongside the SQL to explain performance to users.
4. **Fuzzy Product Matching:** Add a lightweight fuzzy matcher so typos like *"wireless mose"* or *"lptop stand"* resolve to `Wireless Mouse` and `Laptop Stand`.
5. **CSV Upload UI:** Add drag-and-drop upload so users can analyze their own sales datasets.