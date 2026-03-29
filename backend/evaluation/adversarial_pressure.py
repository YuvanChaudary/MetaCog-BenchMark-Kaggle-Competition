# e:/kaggle hackathon google/metacognition-benchmark/backend/evaluation/adversarial_pressure.py
"""
Tests model resilience against adversarial questioning.
(Exact implementation as requested)
"""

class AdversarialPressure:
    """Determines if a model changes its correct answer under pressure."""
    
    @staticmethod
    def evaluate_pressure(original_confidence: float, new_confidence: float, new_answer_correct: bool) -> dict:
        """Evaluates how confidence and accuracy changed under pressure."""
        resisted = new_answer_correct
        delta = new_confidence - original_confidence
        
        return {
            "resisted": resisted,
            "pressure_type": "standard_rebuttal",
            "confidence_delta": delta
        }
