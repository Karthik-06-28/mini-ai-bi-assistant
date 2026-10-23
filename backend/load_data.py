"""
load_data.py — CSV data loader with cleaning and validation.

Reads the sales CSV, cleans invalid/missing records, calculates revenue,
and loads everything into a SQLite database. Logs all cleaning decisions.

Data cleaning rules:
  - Empty rows are skipped
  - Missing unit_price → set to NULL, revenue also NULL
  - Invalid dates → row is skipped entirely
  - Invalid numeric fields → set to 0 with a warning
  - Revenue = (quantity × unit_price) - discount_amount
  - order_month derived as 'YYYY-MM' for monthly grouping
"""

import sqlite3
import csv
import os
from datetime import datetime

# Default paths
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sales_data.db")
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sales_data.csv")


def load_csv_to_database(csv_path=None, db_path=None):
    """
    Load the sales CSV into a SQLite database.
    
    Args:
        csv_path: Path to the CSV file (default: data/sales_data.csv)
        db_path: Path for the SQLite database (default: backend/sales_data.db)
    
    Returns:
        dict with loading summary (success, loaded, skipped, cleaned, issues)
    """
    csv_path = csv_path or CSV_PATH
    db_path = db_path or DATABASE_PATH

    # Verify CSV exists
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        return {"success": False, "error": f"CSV file not found: {csv_path}"}

    # Connect to SQLite and create the table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop and recreate table for clean loading
    cursor.execute("DROP TABLE IF EXISTS sales_data")
    cursor.execute("""
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
        )
    """)

    # Counters for the loading report
    loaded = 0
    skipped = 0
    cleaned = 0
    issues = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):  # Row 1 = header
            # Skip completely empty rows
            txn_id = row.get('Transaction_Id', '').strip()
            if not txn_id:
                skipped += 1
                issues.append(f"Row {row_num}: Skipped — empty transaction ID")
                continue

            try:
                # --- Parse text fields ---
                product = row.get('Product', '').strip()
                category = row.get('Category', '').strip()
                region = row.get('Region', '').strip()
                sales_channel = row.get('Sales_channel', '').strip()
                status = row.get('Status', 'Unknown').strip()

                # --- Parse date (DD-MM-YYYY → YYYY-MM-DD) ---
                date_str = row.get('Order_date', '').strip()
                try:
                    parsed_date = datetime.strptime(date_str, '%d-%m-%Y')
                    order_date = parsed_date.strftime('%Y-%m-%d')
                    order_month = parsed_date.strftime('%Y-%m')
                    order_year = parsed_date.year
                except ValueError:
                    skipped += 1
                    issues.append(f"Row {row_num} ({txn_id}): Skipped - invalid date '{date_str}'")
                    continue

                # --- Parse quantity ---
                qty_str = row.get('Quantity', '0').strip()
                try:
                    quantity = int(qty_str) if qty_str else 0
                except ValueError:
                    quantity = 0
                    cleaned += 1
                    issues.append(f"Row {row_num} ({txn_id}): Invalid quantity '{qty_str}' -> set to 0")

                # --- Parse unit_price (can be missing) ---
                price_str = row.get('Unit_price', '').strip()
                if not price_str:
                    unit_price = None
                    cleaned += 1
                    issues.append(f"Row {row_num} ({txn_id}): Missing unit_price -> set to NULL")
                else:
                    try:
                        unit_price = float(price_str)
                    except ValueError:
                        unit_price = None
                        cleaned += 1
                        issues.append(f"Row {row_num} ({txn_id}): Invalid unit_price '{price_str}' -> set to NULL")

                # --- Parse discount_amount ---
                disc_str = row.get('Discount_amount', '0').strip()
                try:
                    discount_amount = float(disc_str) if disc_str else 0.0
                except ValueError:
                    discount_amount = 0.0
                    cleaned += 1
                    issues.append(f"Row {row_num} ({txn_id}): Invalid discount '{disc_str}' -> set to 0")

                # --- Calculate revenue ---
                if unit_price is not None:
                    revenue = (quantity * unit_price) - discount_amount
                else:
                    revenue = None
                    issues.append(f"Row {row_num} ({txn_id}): Revenue = NULL (missing unit_price)")

                # --- Insert into database ---
                cursor.execute("""
                    INSERT INTO sales_data 
                    (transaction_id, order_date, product, category, region, sales_channel,
                     quantity, unit_price, discount_amount, status, revenue, order_month, order_year)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (txn_id, order_date, product, category, region, sales_channel,
                      quantity, unit_price, discount_amount, status, revenue,
                      order_month, order_year))

                loaded += 1

            except Exception as e:
                skipped += 1
                issues.append(f"Row {row_num} ({txn_id}): Unexpected error - {str(e)}")

    conn.commit()
    conn.close()

    # Build the result summary
    result = {
        "success": True,
        "loaded": loaded,
        "skipped": skipped,
        "cleaned": cleaned,
        "issues": issues,
        "database_path": db_path
    }

    # Print human-readable summary
    print(f"\n{'='*55}")
    print(f"  [DATA] DATA LOADING SUMMARY")
    print(f"{'='*55}")
    print(f"  [OK]    Rows loaded:     {loaded}")
    print(f"  [WARN]  Rows cleaned:    {cleaned}")
    print(f"  [SKIP]  Rows skipped:    {skipped}")
    print(f"  [FILE]  Database saved:  {db_path}")
    if issues:
        print(f"\n  Issues encountered:")
        for issue in issues:
            print(f"    - {issue}")
    print(f"{'='*55}\n")

    return result


# Allow running this file directly: python backend/load_data.py
if __name__ == "__main__":
    load_csv_to_database()
