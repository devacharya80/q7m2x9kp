from fastapi import FastAPI

app = FastAPI(
    title="Wind Forecast Analytics",
    description="UK national wind generation forecast analysis",
    version="0.1.0",
)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "message": "Wind Forecast Analytics API is running",
    }