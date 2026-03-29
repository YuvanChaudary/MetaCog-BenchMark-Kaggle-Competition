# e:/kaggle hackathon google/metacognition-benchmark/backend/api/response_collector.py
"""
Endpoint for collecting raw model responses.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from ..core.models import CollectedResponse

router = APIRouter()

def _get_submission_router():
    """Lazy import to avoid module-level instantiation crash."""
    from .submission_router import SubmissionRouter
    return SubmissionRouter()

_submission_router = None

@router.post("/", response_model=dict)
async def submit_response(response: CollectedResponse, background_tasks: BackgroundTasks):
    """
    Accepts raw responses and routes them for scoring.
    """
    global _submission_router
    if _submission_router is None:
        _submission_router = _get_submission_router()
    try:
        eval_result = _submission_router.route_and_evaluate(response)
        
        return {
            "status": "success",
            "message": "Response collected and evaluated.",
            "evaluation_result": eval_result.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process response: {str(e)}")
