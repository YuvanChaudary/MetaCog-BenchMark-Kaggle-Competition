"""
Unit tests for the calibration engine.
"""
from backend.evaluation.calibration_engine import CalibrationEngine

def test_calculate_ece():
    predictions = [(0.9, True), (0.8, False)]
    engine = CalibrationEngine(n_bins=10)
    for conf, correct in predictions:
        engine.update(conf, correct, "NUMERIC")
    ece = engine.ece
    assert 0.0 <= ece <= 1.0
