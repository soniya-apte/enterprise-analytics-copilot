from fastapi import FastAPI

app = FastAPI(title="Enterprise Analytics Copilot")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}
