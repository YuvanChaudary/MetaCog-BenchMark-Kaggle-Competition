# e:/kaggle hackathon google/metacognition-benchmark/tests/integration/test_focus_isolation.py
"""
Integration test isolating independent focus scorers.
"""
from backend.evaluation.focus_scorers.error_detect_scorer import ErrorDetectScorer
from unittest.mock import MagicMock

def test_error_detect_isolation():
    scorer = ErrorDetectScorer()

    resp = MagicMock()
    resp.answer_text = "its"
    resp.confidence_text = "90"
    resp.raw_text = "its"

    task = MagicMock()
    task.task_id = "err_01"
    task.difficulty = "easy"
    task.model_extra = {"error_planted": False}

    score = scorer.score(resp, "its", task)
    assert score.area == "error_detection"
