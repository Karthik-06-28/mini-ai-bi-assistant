# 📘 Complete End-to-End User & Execution Guide

---

## 1. What Actually Is This Project?

The **Mini AI Business Intelligence Assistant** is a full-stack, enterprise-grade decision support tool designed for business stakeholders (e.g., sales managers, finance analysts, executives).

### The Problem It Solves:
In most organizations, business users want answers to sales questions like:
- *"What is our total revenue?"*
- *"Which product generated the highest revenue?"*
- *"What is the monthly sales trend?"*

Typically, they must wait for a data analyst to write a SQL query. If they ask a generic AI chatbot (like ChatGPT), the AI might make up numbers (**hallucinate**).

### Our Solution:
This application provides a chat dashboard where users type questions in plain English and receive answers backed by **real database calculations**:
1. It translates the question into an **exact, safe SQL query**.
2. It executes that query on a **read-only SQLite database**.
3. It displays the **natural language answer**, **step-by-step reasoning**, the **raw executed SQL**, **source attribution**, a **supporting data table**, and **interactive Chart.js graphs**.
4. **Zero Hallucination:** The AI never invents numbers; all figures come from SQLite.
5. **Zero Data Destruction:** Multi-layered security makes it physically impossible for any user prompt to delete or tamper with data.

---

## 2. End-to-End Execution Flow: From Start to Finish

Here is the exact lifecycle of the application—which folder starts the process, which file runs next, and how data moves through the system:

```
[Phase 1: Ingestion & ETL]
data/sales_data.csv 
       │
       ▼
backend/load_data.py  ───►  Clean anomalies & calculate revenue  ───►  backend/sales_data.db

[Phase 2: Server Startup]
backend/config.py     ───►  Load environment variables (.env) & database paths
       │
       ▼
backend/app.py        ───►  Start Flask server on http://localhost:5000

[Phase 3: User Interaction]
Browser (User)        ───►  Opens frontend/index.html (Styled by frontend/style.css)
       │
       ▼
frontend/app.js       ───►  Captures question & sends POST /api/ask

[Phase 4: AI & Security Pipeline]
backend/gemini_service.py ──► Gemini 2.0 Flash translates question -> SQL + Reasoning
       │
       ▼
backend/sql_validator.py  ──► 5-Step Security Validator (Blocks DROP, DELETE, comments, semicolons)
       │
       ▼
backend/query_executor.py ──► Executes SQL on SQLite in Read-Only Mode (?mode=ro)
       │
       ▼
backend/gemini_service.py ──► Gemini synthesizes natural language answer using ONLY real DB rows

[Phase 5: Visual Presentation]
frontend/app.js       ───►  Renders answer + reasoning chips + SQL display + Chart.js chart + data table
```

### Detailed File-by-File Breakdown:

| Order | File | Responsibility |
|:---:|---|---|
| **1** | [`data/sales_data.csv`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/data/sales_data.csv) | **Raw Data Source:** Contains 51 real transaction records spanning Jan–Jun 2026. |
| **2** | [`backend/load_data.py`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/backend/load_data.py) | **ETL & Data Cleaner:** Reads CSV, converts `DD-MM-YYYY` to `YYYY-MM-DD`, handles edge cases (`TXN0051` missing unit_price, `TXN0034` zero qty, `TXN0033` returned status), calculates `revenue = (quantity * unit_price) - discount_amount`, and saves into SQLite. |
| **3** | [`backend/sales_data.db`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/backend/sales_data.db) | **Relational Storage:** Serverless SQLite database storing the cleaned `sales_data` table. |
| **4** | [`backend/config.py`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/backend/config.py) | **Configuration:** Loads `.env` file, defines absolute paths, and exports the database schema used for Gemini prompt grounding. |
| **5** | [`backend/app.py`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/backend/app.py) | **Flask Web Server:** Hosts REST API (`/api/health`, `/api/schema`, `/api/ask`) and serves the frontend user interface. |
| **6** | [`frontend/index.html`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/frontend/index.html) | **User Interface:** Clean HTML5 structure with quick-suggestion chips, chat message container, and input bar. |
| **7** | [`frontend/style.css`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/frontend/style.css) | **Modern Aesthetics:** Dark theme with glassmorphism, animated gradients, custom scrollbar, and responsive mobile-ready layout. |
| **8** | [`frontend/app.js`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/frontend/app.js) | **Client Controller:** Manages health status indicator, submits questions, toggles collapsible reasoning, renders Chart.js charts, and formats currency tables. |
| **9** | [`backend/gemini_service.py`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/backend/gemini_service.py) | **AI Brain:** Two-stage Gemini 2.0 Flash integration. Stage 1 generates SQL without fabricating numbers; Stage 2 turns database rows into human narrative. Includes a deterministic fallback for offline test environments. |
| **10** | [`backend/sql_validator.py`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/backend/sql_validator.py) | **Safety Gate:** Scans every SQL query before execution. Blocks dangerous keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`), comments, semicolons, and unknown tables. |
| **11** | [`backend/query_executor.py`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/backend/query_executor.py) | **Execution Engine:** Connects to SQLite strictly in read-only mode (`?mode=ro`). Physical OS-level prevention against any write attempt. |
| **12** | [`tests/`](file:///c:/Users/karthik/OneDrive/Desktop/Mini-AI-%20Business-%20Intelligence-%20Assistant/tests/) | **Quality Assurance:** 34 automated unit and integration tests covering SQL safety, data loading, benchmark queries, and API endpoints. |

---

## 3. Complete Step-by-Step Execution Guide

### Prerequisites
- Python 3.10 or higher installed on your computer.
- A terminal (PowerShell, Command Prompt, or Terminal).

---

### Step 1: Navigate to the Project Root Folder
```bash
cd "c:\Users\karthik\OneDrive\Desktop\Mini-AI- Business- Intelligence- Assistant"
```

---

### Step 2: (Recommended) Create and Activate Virtual Environment
```bash
# Windows (PowerShell or CMD)
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

---

### Step 3: Install Required Libraries
```bash
pip install -r requirements.txt
```
This installs:
- `flask` & `flask-cors` (Backend API & web server)
- `google-generativeai` (Gemini LLM SDK)
- `python-dotenv` (Secure environment variable management)
- `pandas` (Data processing)
- `pytest` (Automated testing framework)

---

### Step 4: Configure Your Gemini API Key
1. Create a `.env` file by copying the template:
   ```bash
   # Windows (PowerShell)
   Copy-Item .env.example .env

   # Windows (CMD)
   copy .env.example .env

   # macOS / Linux
   cp .env.example .env
   ```
2. Open the `.env` file in your code editor and enter your Gemini API key:
   ```env
   GEMINI_API_KEY=AIzaSyYourActualGeminiApiKeyHere
   ```
   *(Note: If you run without an API key, the built-in deterministic engine will answer all benchmark questions automatically!)*

---

### Step 5: Clean and Ingest CSV Data into SQLite
```bash
python backend/load_data.py
```
**Expected Output:**
```text
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

### Step 6: Run the Automated Test Suite
To verify that all 34 tests pass:
```bash
python -m pytest tests/ -v
```
**Expected Output:**
```text
============================= 34 passed in 2.30s ==============================
```

---

### Step 7: Launch the Web Application
```bash
python backend/app.py
```
**Expected Output:**
```text
==================================================
  [START] Mini AI BI Assistant is running!
  [WEB]   Open http://localhost:5000 in your browser
==================================================
```

---

### Step 8: Open in Your Browser
Open your browser and navigate to:
👉 **[http://localhost:5000](http://localhost:5000)**

You can click any of the suggestion chips or type questions:
- *"What is the total revenue?"*
- *"Which product generated the highest revenue?"*
- *"What is the monthly revenue trend?"*
- *"Which region generated the highest sales?"*
- *"How did revenue change between January and February?"*
- *"What are the sales by category?"*
- *"What is the weather in Paris?"* *(Demonstrates out-of-scope anti-hallucination handling)*

---

## 4. What to Push to GitHub (and What NOT to Push)

### ✅ What MUST Be Pushed to GitHub:
Evaluators need to see your source code, tests, documentation, and data:

| Folder / File | Why it must be pushed |
|---|---|
| `backend/` | All backend source code (`app.py`, `gemini_service.py`, `sql_validator.py`, etc.) |
| `frontend/` | UI HTML, CSS styling, and JavaScript logic (`app.js`, `index.html`, `style.css`) |
| `data/` | The raw sales dataset (`sales_data.csv`) |
| `docs/` | Architecture (`ARCHITECTURE.md`), AI usage report (`AI_USAGE.md`), and this guide |
| `tests/` | **Critical:** Deliverable #4 requires automated tests (all 34 tests must be in GitHub) |
| `README.md` | Main documentation and project showcase |
| `requirements.txt` | Dependency list so evaluators can install with `pip install -r requirements.txt` |
| `.env.example` | Safe template showing evaluators what environment variables are needed |
| `.gitignore` | Protects secrets from being committed |

---

### ❌ What MUST NEVER Be Pushed (Already in `.gitignore`):

| File / Pattern | Why it must NEVER be pushed |
|---|---|
| `.env` | **Contains your secret Gemini API key.** Pushing this exposes your credentials publicly. |
| `*.db` (`sales_data.db`) | Database binary files should not be stored in Git. Evaluators generate this by running `python backend/load_data.py`. |
| `venv/`, `.venv/` | Virtual environment folders are huge (hundreds of MBs) and machine-specific. |
| `__pycache__/`, `.pytest_cache/` | Auto-generated Python bytecode and test cache files. |

---

## 5. Step-by-Step GitHub Push Instructions (Open Access)

### Step 1: Verify Git Status
In your project directory, run:
```bash
git status
```
Ensure that `.env` and `sales_data.db` do **not** appear in the list.

### Step 2: Stage and Commit All Project Files
```bash
git add .
git commit -m "feat: complete Mini AI Business Intelligence Assistant with Gemini 2.0 Flash and 34 automated tests"
```

### Step 3: Create a Public Repository on GitHub
1. Open your browser and go to: **[https://github.com/new](https://github.com/new)**
2. In **Repository name**, enter: `mini-ai-bi-assistant`
3. Description: `Mini AI Business Intelligence Assistant with Google Gemini, SQLite, and deterministic SQL grounding.`
4. ⚠️ **Important:** Select **Public** so evaluators have open access to review and run your project without permissions.
5. Leave "Add a README file" **unchecked** (we already created a comprehensive one).
6. Click **Create repository**.

### Step 4: Link and Push to GitHub
Copy and run the following commands in your terminal (replace `<YOUR-GITHUB-USERNAME>` with your actual GitHub username):

```bash
git branch -M main
git remote add origin https://github.com/<YOUR-GITHUB-USERNAME>/mini-ai-bi-assistant.git
git push -u origin main
```

Your repository is now live with open access, full documentation, and 100% passing tests! 🎉
