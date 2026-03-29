# e:/kaggle hackathon google/metacognition-benchmark/backend/task_registry/ground_truth_store.py
"""
O(1) lookup for task ground truths with handling for contested answers.
"""
from typing import Dict, Optional
from .task_loader import TaskLoader
from .task_schema import TaskObject

class GroundTruthStore:
    """In-memory fast-access store for ground truth references from all task files."""
    
    def __init__(self, loader: TaskLoader):
        self._store: Dict[str, TaskObject] = {}
        for focus in ["calib", "error_detect", "correction", "certainty"]:
            for task in loader.load_tasks_by_focus(focus):
                self._store[task.task_id] = task

    def get_ground_truth(self, task_id: str) -> Optional[str]:
        """Retrieves exactly the ground truth answer in O(1) time."""
        task = self._store.get(task_id)
        return task.ground_truth if task else None

    def handle_contested(self, task_id: str) -> bool:
        """Handles cases where ground truth is contested."""
        task = self._store.get(task_id)
        return task.metadata.get("contested", False) if task else False
