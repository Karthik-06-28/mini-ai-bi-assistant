# 💼 Mini AI Business Intelligence Assistant

An AI-powered Business Intelligence application that lets business stakeholders ask questions about sales data in plain natural language and receive verified, deterministic answers backed by real SQL database queries.

Powered by **Google Gemini 3.5 Flash Lite**, **SQLite**, and **Flask**, with **zero-hallucination grounding**, **step-by-step reasoning**, and **full source attribution**.

---

## 🌟 Key Features

1. **Deterministic Grounding (Zero Hallucination):** The LLM translates natural language questions into safe SQL and summarizes real query outputs. All calculations are executed by the database engine.
2. **Step-by-Step Reasoning:** Every query shows transparent analytical steps explaining how the answer was reached.
3. **Full Source Attribution:** Every response discloses the source database, table, rows evaluated, and connection mode (`Read-Only`).
4. **3-Tier SQL Safety Guard:**
   - **Tier 1:** Model system prompt strictly configured for `SELECT` queries only.
   - **Tier 2:** Static code sanitizer blocks dangerous keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`), multiple statements (semicolons), and SQL comments.
   - **Tier 3:** SQLite connection opened in physical read-only mode (`?mode=ro`).
5. **Out-of-Scope Detection:** Questions not answerable from the dataset (e.g. weather, stock prices, CEO names) are politely flagged as unanswerable, with helpful alternative suggestions.
6. **Data Cleaning & Anomaly Handling:** Handles missing unit prices (`TXN0051`), zero quantities (`TXN0034`), and returned items (`TXN0033`).
7. **Interactive Visualizations:** Renders charts dynamically with **Chart.js** (bars, trends, proportions) alongside supporting data tables.
8. **Automated Test Suite:** 34 passing tests covering data loading, query determinism, API endpoints, SQL injection prevention, and edge cases.

---

## 📊 Benchmark Business Questions Supported

| # | Question | Ground Truth Result | Visual |
|---|----------|---------------------|--------|
| 1 | **What is the total revenue?** | **₹14,39,200.00** across 49 completed orders | Metric Card |
| 2 | **Which product generated the highest revenue?** | **Monitor** (₹4,73,000.00) | Bar Chart |
| 3 | **What is the monthly revenue trend?** | Jan: ₹2.10L → Feb: ₹2.34L → Mar: ₹2.23L → Apr: ₹2.40L → **May: ₹3.18L (Peak)** → Jun: ₹2.11L | Line Chart |
| 4 | **Which region generated the highest sales?** | **South** (₹4,11,200.00) | Bar Chart |
| 5 | **How did revenue change between two months?** | Jan (₹2,10,250) vs Feb (₹2,34,600) → **+₹24,350 (+11.58%)** | Bar Comparison |

---

## 🛠️ Technology Stack

- **Backend:** Python 3.10+, Flask, Flask-CORS
- **AI / LLM:** Google Gemini 3.5 Flash Lite (`google-generativeai`)
- **Database:** SQLite3 (serverless, zero-install, read-only connection mode)
- **Frontend:** Vanilla HTML5, modern CSS (glassmorphism, custom design tokens), JavaScript (ES6+)
- **Charts:** Chart.js (CDN-delivered)
- **Testing:** Pytest (34 automated test cases)

---

## 📁 Project Structure

```
Mini-AI-Business-Intelligence-Assistant/
├── backend/
│   ├── app.py                  # Flask API server & static file host
│   ├── config.py               # Central paths, schema, and environment loader
│   ├── gemini_service.py       # Gemini 3.5 Flash Lite integration + deterministic fallback
│   ├── load_data.py            # CSV ETL cleaner & SQLite database loader
│   ├── query_executor.py       # Read-only (?mode=ro) SQLite execution engine
│   ├── sql_validator.py        # Regex-based SQL safety validator
│   └── sales_data.db           # SQLite database (auto-generated)
├── data/
│   └── sales_data.csv          # Source sales transaction dataset
├── docs/
│   ├── ARCHITECTURE.md         # System architecture & Mermaid flowcharts
│   └── AI_USAGE.md             # AI tools used, debugging report & future roadmap
├── frontend/
│   ├── index.html              # Main chat & BI dashboard interface
│   ├── style.css               # Glassmorphic dark-theme styles & tokens
│   └── app.js                  # Chat controller, Chart.js renderer & collapsibles
├── tests/
│   ├── test_api.py             # Flask API endpoint integration tests (12 tests)
│   ├── test_loader.py          # Data loading & cleaning edge case tests (6 tests)
│   ├── test_queries.py         # Benchmark BI question tests (5 tests)
│   └── test_sql_validator.py   # SQL safety & injection prevention tests (11 tests)
├── .env.example                # Environment variable template
├── .gitignore                  # Excludes secrets (.env) and DB files
├── requirements.txt            # Python dependencies
└── README.md                   # Project overview and setup guide
```

---

## 🚀 Setup and Execution

### Prerequisites
- Python 3.10 or higher ([Download Python](https://www.python.org/downloads/))
- A Google Gemini API key ([Get a free key at Google AI Studio](https://aistudio.google.com/apikey))

### Step 1: Clone the Repository and Open It

```bash
git clone https://github.com/Karthik-06-28/mini-ai-bi-assistant.git
cd mini-ai-bi-assistant
```

### Step 2: (Recommended) Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Your Gemini API Key

1. Copy the example environment file:
   ```bash
   # Windows (PowerShell)
   Copy-Item .env.example .env

   # Windows (CMD)
   copy .env.example .env

   # macOS / Linux
   cp .env.example .env
   ```

2. Open `.env` and paste your Gemini API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

> 🔒 **Security Notice:** `.env` is listed in `.gitignore` and is never committed to the repository. Each user supplies their own API key locally.

### Step 5: Load and Clean the Sales Data

Run the ETL loader to create and populate the SQLite database:

```bash
python backend/load_data.py
```

Expected output:
```
=======================================================
  [DATA] DATA LOADING SUMMARY
=======================================================
  [OK]    Rows loaded:     51
  [WARN]  Rows cleaned:    1
  [SKIP]  Rows skipped:    0
  [FILE]  Database saved:  .../backend/sales_data.db

  Issues encountered:
    - Row 52 (TXN0051): Missing unit_price -> set to NULL
    - Row 52 (TXN0051): Revenue = NULL (missing unit_price)
=======================================================
```

### Step 6: Start the Application Server

```bash
python backend/app.py
```

Expected output:
```
==================================================
  [START] Mini AI BI Assistant is running!
  [WEB]   Open http://localhost:5000 in your browser
==================================================
```

### Step 7: Open the Application

Navigate to **[http://localhost:5000](http://localhost:5000)**.Type a question in the chat box, for example:

- *"What is the total revenue?"*
- *"Which product generated the highest revenue?"*
- *"What is the monthly revenue trend?"*
- *"Which region generated the highest sales?"*
- *"How did revenue change between January and February?"*
- *"What are the sales by category?"*
- *"What is the weather today?"* *(demonstrates out-of-scope handling)*

---

## 🧪 Running the Automated Tests

```bash
python -m pytest tests/ -v
```

All 34 tests across 4 modules should pass:

- **`tests/test_sql_validator.py`** (11 tests): safe SELECT queries, and blocking of DROP, DELETE, UPDATE, INSERT, semicolons, comments, and unauthorized tables.
- **`tests/test_loader.py`** (6 tests): CSV ingestion, date normalization, revenue formula, missing unit prices, zero quantities, and returned items.
- **`tests/test_queries.py`** (5 tests): exact deterministic results for each of the 5 benchmark business questions.
- **`tests/test_api.py`** (12 tests): `/api/health`, `/api/schema`, `/api/ask`, input validation (empty/oversized strings), out-of-scope handling, and SQL injection blocking.

---

## 📚 Further Documentation

- [**Architecture & Technical Design**](docs/ARCHITECTURE.md): data flow, security layers, grounding strategy, and schema.
- [**AI Usage & Engineering Report**](docs/AI_USAGE.md): AI tools used, problems encountered, and future improvements.
