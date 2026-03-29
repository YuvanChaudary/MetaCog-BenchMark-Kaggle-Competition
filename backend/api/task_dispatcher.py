# e:/kaggle hackathon google/metacognition-benchmark/backend/api/task_dispatcher.py
"""
Endpoints for dispatching tasks to evaluate.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List
from ..core.models import RawResponse
from ..task_registry.task_loader import TaskLoader
from ..task_registry.task_schema import TaskObject

from ..core.config import settings
router = APIRouter()
loader = TaskLoader(task_bank_path=settings.TASK_BANK_PATH)

@router.get("/", response_model=TaskObject)
async def get_task(focus_area: str = Query(..., description="E.g., calibration, error_detect, certainty, correction")):
    """Retrieves a single task for the specific focus area."""
    try:
        tasks = list(loader.load(focus_area=focus_area, limit=1))
        if not tasks:
            raise HTTPException(status_code=404, detail="No tasks found for focus area")
        # Returning first task for MVP simplicity; random/sequential logic can be added
        return tasks[0]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch", response_model=List[TaskObject])
async def get_task_batch(focus_area: str = Query(...), limit: int = 5):
    """Retrieves a batch of tasks."""
    try:
        tasks = list(loader.load(focus_area=focus_area, limit=limit))
        return tasks
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
