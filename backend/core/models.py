# e:/kaggle hackathon google/metacognition-benchmark/backend/core/models.py
"""
Shared Pydantic models utilized across all modules.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, ConfigDict

class RawResponse(BaseModel):
    """Raw response received from the model."""
    task_id: str
    raw_text: str
    metadata: Dict[str, Any] = {}

class CollectedResponse(BaseModel):
    """Response collected from the /response endpoint."""
    session_id: str
    response: RawResponse
    timestamp: float

class ParsedResponse(BaseModel):
    """Parsed response containing extracted answer and confidence."""
    task_id: str
    extracted_answer: str
    confidence_score: float
    raw_text: str

class FocusScore(BaseModel):
    """Score for a specific metacognition focus area."""
    focus_area: str
    score: float
    details: Dict[str, Any] = {}

class PressureResult(BaseModel):
    """Result of adversarial pressure evaluation."""
    resisted: bool
    pressure_type: str
    confidence_delta: float

class AnomalyReport(BaseModel):
    """Report for detected anomalies like sycophancy or evasion."""
    anomaly_type: str
    severity: float
    evidence: str

class EvaluationResult(BaseModel):
    """Result of evaluating a single response."""
    task_id: str
    parsed_response: ParsedResponse
    focus_scores: List[FocusScore]
    pressure_result: Optional[PressureResult] = None
    anomaly_report: Optional[AnomalyReport] = None

class MetaCogResult(BaseModel):
    """Aggregated metacognition benchmark result."""
    session_id: str
    overall_score: float
    evaluations: List[EvaluationResult]
    aggregated_metrics: Dict[str, float]
