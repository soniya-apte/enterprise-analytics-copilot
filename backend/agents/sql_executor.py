"""
Safe SQL validation and execution against the AdventureWorks database.
Enforces read-only (SELECT) queries as a hard safety guardrail.
"""
import re
from sqlalchemy import text
from database import aw_engine

# Keywords that indicate a write/destructive operation — forbidden.
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|REPLACE)\b",
    re.IGNORECASE,
)


def validate_sql(sql: str) -> tuple[bool, str]:
    """Return (is_valid, reason). Only single SELECT statements are allowed."""
    stripped = sql.strip().rstrip(";").strip()

    if not stripped:
        return False, "Empty query."

    # Must start with SELECT (or WITH for CTEs)
    if not re.match(r"^(SELECT|WITH)\b", stripped, re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    # No forbidden write keywords
    if FORBIDDEN.search(stripped):
        return False, "Query contains a forbidden write/DDL keyword."

    # Disallow multiple statements (prevent SQL injection via ';')
    if ";" in stripped:
        return False, "Multiple statements are not allowed."

    return True, "OK"


def execute_sql(sql: str, row_limit: int = 100) -> dict:
    """Validate then execute a read-only SQL query. Returns rows + columns."""
    is_valid, reason = validate_sql(sql)
    if not is_valid:
        return {"success": False, "error": reason, "rows": [], "columns": []}

    try:
        with aw_engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchmany(row_limit)]
        return {
            "success": True,
            "error": None,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "rows": [], "columns": []}
