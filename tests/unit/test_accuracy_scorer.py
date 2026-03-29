"""
Unit tests for the accuracy scorer.
"""
from backend.evaluation.accuracy_scorer import AccuracyScorer

def test_accuracy_exact_match():
    scorer = AccuracyScorer()
    result = scorer.score("Paris", "Paris")
    assert result.correct == True

def test_accuracy_partial_match():
    scorer = AccuracyScorer()
    result = scorer.score("It is Paris", "Paris")
    assert result.correct == True
