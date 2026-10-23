"""
app.py — Flask API server for the Mini AI BI Assistant.

Endpoints:
  GET  /              → Serve the frontend UI
  GET  /api/health    → Health check + database status
  GET  /api/schema    → Database schema & metadata
  POST /api/ask       → Accept a question, return grounded answer
  POST /api/load-data → Reload CSV into the database

The /api/ask endpoint follows a strict pipeline:
  1. Validate the user's input
  2. Send question to Gemini → get SQL + reasoning (Stage 1)
  3. Validate the generated SQL for safety
  4. Execute the query on the read-only database
  5. Send results to Gemini → get human-readable answer (Stage 2)
  6. Return everything: answer, reasoning, SQL, source info, data, chart
"""

import os
import sys

# Add backend directory to Python path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from sql_validator import validate_sql, sanitize_sql
from query_executor import execute_query, get_table_info
from gemini_service import generate_sql_from_question, generate_answer_from_results
from load_data import load_csv_to_database

# Flask app — serves both the API and the frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)


# ──────────────────────────────
#  Static File Serving
# ──────────────────────────────

@app.route('/')
def serve_frontend():
    """Serve the main HTML page."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve CSS, JS, and other static files."""
    return send_from_directory(app.static_folder, filename)


# ──────────────────────────────
#  API Endpoints
# ──────────────────────────────

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check — confirms the server is running and database is loaded."""
    db_info = get_table_info()
    return jsonify({
        "status": "healthy",
        "database_loaded": db_info is not None,
        "row_count": db_info["row_count"] if db_info else 0
    })


@app.route('/api/schema', methods=['GET'])
def get_schema():
    """Return database schema, column info, and available values for the UI."""
    info = get_table_info()
    if not info:
        return jsonify({"error": "Database not loaded. Run load_data.py first."}), 500
    return jsonify(info)


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """
    Main endpoint — accepts a natural language question and returns
    a grounded, traceable answer.

    Request body: { "question": "What is the total revenue?" }
    
    Response includes:
    - answer: Human-readable answer
    - reasoning_steps: How the answer was derived
    - sql_query: The exact SQL used
    - source: Database, table, row count, columns
    - data: Raw query results
    - chart_type: Suggested visualization
    """
    data = request.get_json()

    # ── Input Validation ──
    if not data or 'question' not in data:
        return jsonify({
            "success": False,
            "error": "Request must include a 'question' field. Example: {\"question\": \"What is the total revenue?\"}"
        }), 400

    question = data['question'].strip()

    if not question:
        return jsonify({
            "success": False,
            "error": "Question cannot be empty. Please type a question about the sales data."
        }), 400

    if len(question) > 500:
        return jsonify({
            "success": False,
            "error": "Question is too long (max 500 characters). Please be more concise."
        }), 400

    # ── STEP 1: Gemini generates SQL + reasoning (no data fabrication) ──
    gemini_response = generate_sql_from_question(question)

    if not gemini_response.get("success"):
        return jsonify({
            "success": False,
            "error": gemini_response.get("error", "Failed to process the question with AI."),
            "step_failed": "AI Processing (Stage 1: Text-to-SQL)"
        }), 500

    # ── STEP 2: Check if question is answerable from the data ──
    if not gemini_response.get("is_answerable", False):
        return jsonify({
            "success": False,
            "is_answerable": False,
            "reason": gemini_response.get("reason", "This question cannot be answered from the sales dataset."),
            "suggestion": gemini_response.get("suggestion", "Try asking about revenue, products, regions, or monthly trends."),
            "reasoning_steps": [
                "Step 1: Analyzed the user's question",
                "Step 2: Checked available data in the sales_data table",
                "Step 3: Determined the question is outside the scope of this dataset"
            ]
        }), 200  # 200 because the API worked correctly — the question is just out of scope

    sql_query = gemini_response.get("sql_query", "")

    # ── STEP 3: Validate SQL for safety ──
    sql_query = sanitize_sql(sql_query)
    is_valid, validation_msg = validate_sql(sql_query)

    if not is_valid:
        return jsonify({
            "success": False,
            "error": f"Generated SQL failed safety validation: {validation_msg}",
            "sql_query": sql_query,
            "step_failed": "SQL Safety Validation"
        }), 400

    # ── STEP 4: Execute validated query on read-only database ──
    query_result = execute_query(sql_query)

    if not query_result["success"]:
        return jsonify({
            "success": False,
            "error": query_result["error"],
            "sql_query": sql_query,
            "step_failed": "Database Query Execution"
        }), 500

    # ── STEP 5: Gemini generates human-readable answer from REAL results ──
    answer_response = generate_answer_from_results(
        question, sql_query, query_result["data"]
    )

    # Fallback answer if Gemini Stage 2 fails
    answer_text = answer_response.get("answer", "Query executed successfully. See the data below.")
    highlights = answer_response.get("highlights", [])

    # ── STEP 6: Build the complete, grounded response ──
    response = {
        "success": True,
        "question": question,

        # The answer (grounded in real data)
        "answer": answer_text,
        "highlights": highlights,

        # How the answer was derived (transparency)
        "reasoning_steps": gemini_response.get("reasoning_steps", []),

        # The exact SQL query used (full traceability)
        "sql_query": sql_query,

        # Source information (where the data came from)
        "source": {
            "database": "SQLite (sales_data.db)",
            "table": "sales_data",
            "rows_returned": query_result["row_count"],
            "columns_returned": query_result.get("columns", []),
            "connection_mode": "Read-Only"
        },

        # Raw data from the database
        "data": query_result["data"],

        # Visualization hints
        "chart_type": gemini_response.get("chart_type", "table"),
        "chart_config": gemini_response.get("chart_config", {})
    }

    return jsonify(response), 200


@app.route('/api/load-data', methods=['POST'])
def reload_data():
    """Reload the CSV file into the database (for admin use)."""
    result = load_csv_to_database()
    if result["success"]:
        return jsonify(result), 200
    else:
        return jsonify(result), 500


# ──────────────────────────────
#  Application Startup
# ──────────────────────────────

if __name__ == '__main__':
    # Auto-load data if database doesn't exist yet
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sales_data.db")
    if not os.path.exists(db_path):
        print("[INFO] Database not found. Loading CSV data...")
        load_csv_to_database()

    print("\n" + "=" * 50)
    print("  [START] Mini AI BI Assistant is running!")
    print("  [WEB]   Open http://localhost:5000 in your browser")
    print("=" * 50 + "\n")

    app.run(debug=True, port=5000, host='0.0.0.0')
