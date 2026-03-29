# e:/kaggle hackathon google/metacognition-benchmark/tests/unit/test_adversarial_pressure.py
"""
Unit tests for adversarial pressure evaluation.
"""
from backend.evaluation.adversarial_pressure import AdversarialPressure

def test_evaluate_pressure():
    result = AdversarialPressure.evaluate_pressure(0.9, 0.4, False)
    assert result["resisted"] is False
    assert round(result["confidence_delta"], 2) == -0.50
