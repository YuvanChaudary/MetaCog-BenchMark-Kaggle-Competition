# e:/kaggle hackathon google/metacognition-benchmark/backend/api/health.py
"""
Liveness check for container orchestration and uptime monitoring.
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/health", response_model=dict)
async def check_health():
    """Returns basic health status."""
    return {"status": "ok", "version": "1.0.0"}
