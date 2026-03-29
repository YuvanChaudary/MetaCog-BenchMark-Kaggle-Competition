"""
Unit tests for the score aggregator.
"""
from backend.evaluation.score_aggregator import MetaCogAggregator, FocusScore

def test_aggregate():
    aggregator = MetaCogAggregator()

    focus_scores = {
        "calibration": FocusScore(
            area="calibration", score=72.0, n_tasks=10,
            dominant_failure="well_calibrated",
            confidence_interval=(0.65, 0.79)
        ),
        "error_detection": FocusScore(
            area="error_detection", score=65.0, n_tasks=10,
            dominant_failure="accurate_error_detection",
            confidence_interval=(0.58, 0.72)
        ),
        "correction": FocusScore(
            area="correction", score=58.0, n_tasks=10,
            dominant_failure="justified_not_fixed",
            confidence_interval=(0.50, 0.66)
        ),
        "certainty": FocusScore(
            area="certainty", score=70.0, n_tasks=10,
            dominant_failure="accurate_epistemic_self_assessment",
            confidence_interval=(0.63, 0.77)
        ),
    }

    result = aggregator.aggregate(
        focus_scores=focus_scores,
        anomaly_penalty=0.1,
        run_id="test-run-001",
        model_id="gpt-4o"
    )
    assert 0.0 <= result.metacog_index <= 100.0
    assert result.model_id == "gpt-4o"
