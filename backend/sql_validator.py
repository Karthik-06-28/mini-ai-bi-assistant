"""
sql_validator.py — SQL safety validation layer.

Ensures ONLY safe SELECT queries are executed against the database.
Three levels of protection:
  1. Keyword blocklist (DROP, DELETE, INSERT, etc.)
  2. Must start with SELECT
  3. Must only reference the sales_data table
"""

import re

# Dangerous SQL keywords that could modify or destroy data
DANGEROUS_KEYWORDS = [
    r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bDROP\b',
    r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'\bREPLACE\b',
    r'\bEXEC\b', r'\bEXECUTE\b', r'\bGRANT\b', r'\bREVOKE\b',
    r'\bATTACH\b', r'\bDETACH\b', r'\bPRAGMA\b', r'\bVACUUM\b',
    r'\bREINDEX\b', r'\bBEGIN\b', r'\bCOMMIT\b', r'\bROLLBACK\b',
    r'\bSAVEPOINT\b', r'\bRELEASE\b'
]

# Only these columns exist in our database
VALID_COLUMNS = [
    "transaction_id", "order_date", "product", "category", "region",
    "sales_channel", "quantity", "unit_price", "discount_amount",
    "status", "revenue", "order_month", "order_year"
]


def validate_sql(sql_query):
    """
    Validate a SQL query for safety before execution.
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    
    Checks performed:
        1. Not empty
        2. Starts with SELECT
        3. No multiple statements (semicolons)
        4. No dangerous keywords (DROP, DELETE, etc.)
        5. No SQL comments (could hide malicious code)
        6. Only references the 'sales_data' table
    """
    if not sql_query or not sql_query.strip():
        return False, "Empty SQL query"

    # Remove trailing semicolons and whitespace for analysis
    cleaned = sql_query.strip().rstrip(';').strip()

    # CHECK 1: Must start with SELECT
    if not re.match(r'^\s*SELECT\b', cleaned, re.IGNORECASE):
        return False, "Only SELECT queries are allowed. Query must start with SELECT."

    # CHECK 2: Block multiple statements (semicolons in the middle)
    if ';' in cleaned:
        return False, "Multiple SQL statements are not allowed."

    # CHECK 3: Scan for dangerous keywords
    for pattern in DANGEROUS_KEYWORDS:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            return False, f"Dangerous SQL keyword detected: '{match.group()}'. Only SELECT queries are allowed."

    # CHECK 4: Block SQL comments (could hide malicious SQL)
    if '--' in cleaned or '/*' in cleaned:
        return False, "SQL comments are not allowed for security reasons."

    # CHECK 5: Ensure only the sales_data table is referenced
    table_refs = re.findall(r'\bFROM\s+(\w+)', cleaned, re.IGNORECASE)
    join_refs = re.findall(r'\bJOIN\s+(\w+)', cleaned, re.IGNORECASE)
    all_tables = table_refs + join_refs

    for table in all_tables:
        if table.lower() != 'sales_data':
            return False, f"Unknown table: '{table}'. Only 'sales_data' table is available."

    return True, "Query is valid and safe to execute."


def sanitize_sql(sql_query):
    """
    Clean up a SQL query string:
    - Strip whitespace
    - Remove trailing semicolons
    """
    if not sql_query:
        return ""
    return sql_query.strip().rstrip(';').strip()
