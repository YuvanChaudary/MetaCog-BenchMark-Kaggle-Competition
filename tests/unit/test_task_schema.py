# e:/kaggle hackathon google/metacognition-benchmark/tests/unit/test_task_schema.py
"""
Unit tests for the TaskObject schema.
"""
from backend.task_registry.task_schema import TaskObject

def test_task_schema_instantiation():
    task = TaskObject(
        task_id="t1",
        focus_area="calib",
        prompt="Test",
        ground_truth="Answer"
    )
    assert task.task_id == "t1"
    assert task.metadata == {}
