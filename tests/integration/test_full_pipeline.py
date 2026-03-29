# e:/kaggle hackathon google/metacognition-benchmark/tests/integration/test_full_pipeline.py
"""
Integration tests for the full evaluation pipeline.
"""
from unittest.mock import MagicMock, patch
from backend.api.submission_router import SubmissionRouter


def test_pipeline_routing():
    with patch("backend.api.submission_router.TaskLoader") as MockLoader, \
         patch("backend.api.submission_router.GroundTruthStore") as MockGT:
        mock_loader_inst = MagicMock()
        MockLoader.return_value = mock_loader_inst
        MockGT.return_value = MagicMock()

        router = SubmissionRouter()
        assert router is not None
        assert router.anomaly_detector is not None
