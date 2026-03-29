"""
Unit tests for the confidence parser.
"""
from backend.evaluation.confidence_parser import parse_confidence_safe

def test_confidence_parser():
    raw = "The answer is 42. \nConfidence: 85%"
    conf, method = parse_confidence_safe(raw)
    assert 0.0 <= conf <= 1.0
    assert method in ["NUMERIC","PERCENTAGE","VERBAL_MAP","SENTIMENT","DEFAULT_FALLBACK"]
