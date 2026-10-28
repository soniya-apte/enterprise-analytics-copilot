from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from api.service import ask, get_answer, history
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


# ---------------- Copilot API ----------------

class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, description="A business question in plain English")


@app.post("/ask")
def ask_endpoint(req: AskRequest):
    """Run the full multi-agent pipeline on one question and return the answer."""
    try:
        return ask(req.question.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")


@app.get("/history")
def history_endpoint(limit: int = 20):
    """Most recent questions asked through /ask."""
    return history(min(max(limit, 1), 100))


@app.get("/history/{qid}")
def history_item(qid: int):
    """The full stored answer for one past question."""
    resp = get_answer(qid)
    if resp is None:
        raise HTTPException(status_code=404, detail=f"No question with id {qid}")
    return resp
