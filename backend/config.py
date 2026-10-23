"""
config.py — Central configuration for the BI Assistant.
Loads environment variables and defines constants used across the application.
"""

import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "sales_data.db")
CSV_PATH = os.path.join(BASE_DIR, "..", "data", "sales_data.csv")

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Database Schema (used in Gemini prompts for grounding) ---
TABLE_SCHEMA = """
CREATE TABLE sales_data (
    transaction_id TEXT PRIMARY KEY,
    order_date TEXT,
    product TEXT,
    category TEXT,
    region TEXT,
    sales_channel TEXT,
    quantity INTEGER,
    unit_price REAL,
    discount_amount REAL,
    status TEXT,
    revenue REAL,
    order_month TEXT,
    order_year INTEGER
);
"""

# Columns that exist in the database — used for validation
VALID_COLUMNS = [
    "transaction_id", "order_date", "product", "category", "region",
    "sales_channel", "quantity", "unit_price", "discount_amount",
    "status", "revenue", "order_month", "order_year"
]
