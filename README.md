# 💼 Mini AI Business Intelligence Assistant

An AI-powered Business Intelligence application that enables business stakeholders to ask questions about sales data using plain natural language and receive verified, deterministic answers backed by real SQL database queries.

Powered by **Google Gemini 2.0 Flash**, **SQLite**, and **Flask**, with **100% zero-hallucination grounding**, **step-by-step reasoning**, and **full source attribution**.

> 📖 **Looking for the complete start-to-finish execution guide?** Read the [**Complete User & Execution Guide**](docs/COMPLETE_USER_GUIDE.md) for step-by-step file lifecycles, execution commands, and GitHub submission instructions.

---

## 🌟 Key Features

1. **Deterministic Grounding (Zero Hallucination):** The LLM translates natural language questions into safe SQL and summarizes real query outputs. All calculations are executed by the database engine.
2. **Step-by-Step Reasoning:** Every query shows transparent analytical steps explaining how the answer was reached.
3. **Full Source Attribution:** Every response explicitly discloses the source database, table, rows evaluated, and connection mode (`Read-Only`).
4. **3-Tier SQL Safety Guard:**
   - **Tier 1:** Model system prompt strictly configured for `SELECT` queries only.
   - **Tier 2:** Static code sanitizer blocks dangerous keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`), multiple statements (semicolons), and SQL comments.
   - **Tier 3:** SQLite connection opened in physical read-only mode (`?mode=ro`).
5. **Out-of-Scope Detection:** Questions not present in the dataset (e.g. weather, stock prices, CEO names) are politely flagged as unanswerable with helpful alternative suggestions.
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
- **AI / LLM:** Google Gemini 2.0 Flash (`google-generativeai`)
- **Database:** SQLite3 (Serverless, zero-install, read-only connection mode)
- **Frontend:** Vanilla HTML5, Modern CSS (Glassmorphism, custom design tokens), JavaScript (ES6+)
- **Charts:** Chart.js (CDN-delivered)
- **Testing:** Pytest (34 automated test cases)

---

## 📁 Project Structure

```
Mini-AI-Business-Intelligence-Assistant/
├── backend/
│   ├── app.py                  # Flask API server & static file host
│   ├── config.py               # Central paths, schema, and environment loader
│   ├── gemini_service.py       # Gemini 2.0 Flash integration + deterministic fallback
│   ├── load_data.py            # CSV ETL cleaner & SQLite database loader
│   ├── query_executor.py       # Read-only (?mode=ro) SQLite execution engine
│   ├── sql_validator.py        # 5-step AST/regex SQL safety validator
│   └── sales_data.db           # SQLite database (auto-generated)
├── data/
│   └── sales_data.csv          # Clean source sales transaction dataset
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
│   ├── test_queries.py         # Benchmark BI questions tests (5 tests)
│   └── test_sql_validator.py   # SQL safety & injection prevention tests (11 tests)
├── .env.example                # Safe environment variable template
├── .gitignore                  # Prevents secrets (.env) and DB files from Git
├── requirements.txt            # Python dependencies
└── README.md                   # Setup, execution, and submission guide
```

---

## 🚀 Step-by-Step Setup and Execution Instructions

### Prerequisites
- Python 3.10 or higher installed ([Download Python](https://www.python.org/downloads/))
- Git installed ([Download Git](https://git-scm.com/))
- Google Gemini API Key ([Get a free key at Google AI Studio](https://aistudio.google.com/apikey))

---

### Step 1: Open the Project Directory
Open your terminal (PowerShell, Command Prompt, or Bash) and navigate to the project directory:

```bash
cd "c:\Users\karthik\OneDrive\Desktop\Mini-AI- Business- Intelligence- Assistant"
```

---

### Step 2: (Optional but Recommended) Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

---

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4: Configure Your Gemini API Key in `.env`

1. Copy the `.env.example` file to create your own `.env` file:
   ```bash
   # Windows (PowerShell)
   Copy-Item .env.example .env

   # Windows (CMD)
   copy .env.example .env

   # macOS / Linux
   cp .env.example .env
   ```

2. Open the `.env` file in your editor and paste your Gemini API key:
   ```env
   GEMINI_API_KEY=AIzaSyYourActualGeminiApiKeyHere
   ```

> 🔒 **Security Notice:** The `.env` file is explicitly listed in `.gitignore` and will **never** be committed or pushed to GitHub. Evaluators can clone the repository, add their own API key to their local `.env`, and run the app immediately.

---

### Step 5: Ingest and Clean the Sales CSV into SQLite

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

---

### Step 6: Start the Application Server

Start the Flask backend server:

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

---

### Step 7: Open the Application in Your Browser

Open your browser and navigate to:
👉 **[http://localhost:5000](http://localhost:5000)**

You can click any of the suggestion chips on the screen or type any question:
- *"What is the total revenue?"*
- *"Which product generated the highest revenue?"*
- *"What is the monthly revenue trend?"*
- *"Which region generated the highest sales?"*
- *"How did revenue change between January and February?"*
- *"What are the sales by category?"*
- *"What is the weather today?"* *(Demonstrates out-of-scope anti-hallucination handling)*

---

## 🧪 Running Automated Tests

Run the complete test suite (34 automated tests across 4 test modules):

```bash
python -m pytest tests/ -v
```

All 34 test cases will execute and pass:
- **`tests/test_sql_validator.py`**: 11 tests verifying safe SELECT queries and blocking DROP, DELETE, UPDATE, INSERT, semicolons, comments, and unauthorized tables.
- **`tests/test_loader.py`**: 6 tests verifying CSV ingestion, date normalization, revenue formula, missing unit prices, zero quantities, and returned items.
- **`tests/test_queries.py`**: 5 tests verifying exact deterministic calculations for each of the 5 benchmark business questions.
- **`tests/test_api.py`**: 12 tests verifying `/api/health`, `/api/schema`, `/api/ask`, input validation (empty/oversized strings), anti-hallucination out-of-scope handling, and SQL injection blocking.

---

## 🌐 Step-by-Step GitHub Submission Guide (Open Access)

Follow these exact steps to create a Git repository, commit your project, and push it to GitHub with open public access for evaluators:

### 1. Initialize Git in the Project Folder
```bash
git init
```

### 2. Verify `.gitignore` is Protecting Your Secrets
Run:
```bash
git status
```
Ensure that `.env` and `*.db` do **not** appear in the untracked files list. Only safe files like `.env.example`, `backend/`, `data/`, `frontend/`, `tests/`, `docs/`, and `README.md` should be listed.

### 3. Stage and Commit All Files
```bash
git add .
git commit -m "feat: complete Mini AI Business Intelligence Assistant with Gemini 2.0 Flash, zero-hallucination grounding, and 34 automated tests"
```

### 4. Create a New Public Repository on GitHub
1. Go to [https://github.com/new](https://github.com/new) in your browser.
2. In the **Repository name** field, enter: `mini-ai-bi-assistant`
3. Description: `Mini AI Business Intelligence Assistant powered by Google Gemini and SQLite with deterministic SQL grounding.`
4. ⚠️ **IMPORTANT (Open Access for Evaluation):** Select **Public** so evaluators can view and clone your code without requiring permission.
5. Do **not** initialize with a README, .gitignore, or license (you already have them).
6. Click **Create repository**.

### 5. Link Local Repository and Push to GitHub
Copy the commands shown on GitHub (replace `<YOUR-USERNAME>` with your GitHub username):

```bash
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/mini-ai-bi-assistant.git
git push -u origin main
```

Your repository is now live with full open access for evaluation! 🎉

---

## 🛡️ Evaluation Checklist & Deliverables Verification

| Deliverable Required | Location in Repository | Status |
|----------------------|------------------------|--------|
| **1. Source code in Git repo** | Entire repository (`backend/`, `frontend/`, `data/`) | ✅ Complete |
| **2. README with setup instructions** | [`README.md`](README.md) | ✅ Complete |
| **3. Architecture diagram & explanation** | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | ✅ Complete |
| **4. Automated tests** | [`tests/`](tests/) (34 passing test cases) | ✅ Complete |
| **5. AI tools usage & debugging report** | [`docs/AI_USAGE.md`](docs/AI_USAGE.md) | ✅ Complete |
| **- SQL validation layer** | [`backend/sql_validator.py`](backend/sql_validator.py) | ✅ Complete |
| **- Anti-hallucination grounding** | [`backend/gemini_service.py`](backend/gemini_service.py) | ✅ Complete |
| **- Source traceability metadata** | Exposed via `/api/ask` and displayed in UI | ✅ Complete |
