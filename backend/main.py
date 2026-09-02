from fastapi import FastAPI
from sqlalchemy import text
from database import app_engine, aw_engine

app = FastAPI(title="Enterprise Analytics Copilot")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}

@app.get("/db-check")
def db_check():
    with app_engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), current_user;"))
        row = result.fetchone()
        return {
            "status": "connected",
            "database": row[0],
            "user": row[1]
        }

@app.get("/sales-by-year")
def sales_by_year():
    query = text("""
        SELECT
            EXTRACT(YEAR FROM orderdate) AS year,
            COUNT(*) AS num_orders,
            ROUND(SUM(totaldue)::numeric, 2) AS total_revenue
        FROM sales.salesorderheader
        GROUP BY year
        ORDER BY year;
    """)
    with aw_engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
        return {
            "status": "ok",
            "data": [
                {
                    "year": int(row[0]),
                    "num_orders": row[1],
                    "total_revenue": float(row[2])
                }
                for row in rows
            ]
        }
