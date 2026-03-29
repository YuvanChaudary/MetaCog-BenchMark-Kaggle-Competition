# e:/kaggle hackathon google/metacognition-benchmark/tests/conftest.py
"""
Shared pytest fixtures for the metacognition benchmark.
"""
import pytest
from backend.core.models import ParsedResponse

@pytest.fixture
def sample_parsed_response():
    return ParsedResponse(
        task_id="calib_123",
        extracted_answer="Paris",
        confidence_score=0.9,
        raw_text="Answer: Paris. Confidence: 90%"
    )
