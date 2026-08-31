from fastapi import FastAPI
from sqlalchemy import text
from database import engine

app = FastAPI(title="Enterprise Analytics Copilot")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}

@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), current_user;"))
        row = result.fetchone()
        return {
            "status": "connected",
            "database": row[0],
            "user": row[1]
        }
