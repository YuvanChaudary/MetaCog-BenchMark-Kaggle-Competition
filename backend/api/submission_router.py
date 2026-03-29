# e:/kaggle hackathon google/metacognition-benchmark/backend/api/submission_router.py
"""
Routes collected responses through parsers, scorers, and anomaly detectors.
"""
import time
from ..core.models import CollectedResponse, EvaluationResult, ParsedResponse
from ..evaluation.confidence_parser import parse_confidence_safe
from ..evaluation.anomaly_detector import AnomalyDetector
from ..evaluation.focus_scorers.calib_scorer import CalibScorer
from ..evaluation.focus_scorers.error_detect_scorer import ErrorDetectScorer
from ..evaluation.focus_scorers.correction_scorer import CorrectionScorer
from ..evaluation.focus_scorers.certainty_scorer import CertaintyScorer
from ..task_registry.task_loader import TaskLoader
from ..task_registry.ground_truth_store import GroundTruthStore
from ..core.config import settings

class SubmissionRouter:
    """Pipelines incoming responses through necessary evaluation steps."""
    
    def __init__(self):
        self.parser = parse_confidence_safe
        self.anomaly_detector = AnomalyDetector()
        
        self.loader = TaskLoader(task_bank_path=settings.TASK_BANK_PATH)
        self.gt_store = GroundTruthStore(self.loader)
        
        self.scorers = {
            "calib": CalibScorer(),
            "error_detect": ErrorDetectScorer(),
            "correction": CorrectionScorer(),
            "certainty": CertaintyScorer()
        }

    def route_and_evaluate(self, item: CollectedResponse) -> EvaluationResult:
        """Processes the fully assembled evaluation output in O(n) time and O(1) space per event."""
        raw = item.response
        conf, method = self.parser(raw.raw_text)
        
        parsed = ParsedResponse(
            task_id=raw.task_id,
            extracted_answer=raw.raw_text,
            confidence_score=conf,
            raw_text=raw.raw_text
        )
        
        anomaly = self.anomaly_detector.detect(raw.raw_text)
        gt = self.gt_store.get_ground_truth(raw.task_id) or ""
        
        # Determine focus area based on prefix format (e.g. 'calib_001')
        focus_area = raw.task_id.split('_')[0] if "_" in raw.task_id else "calib"
        
        scorer = self.scorers.get(focus_area, self.scorers["calib"])
        focus_score = scorer.score(parsed, gt)
        
        from ..core.models import AnomalyReport
        anomaly_report = AnomalyReport(**anomaly) if anomaly["anomaly_type"] != "none" else None
        
        return EvaluationResult(
            task_id=raw.task_id,
            parsed_response=parsed,
            focus_scores=[focus_score],
            pressure_result=None,
            anomaly_report=anomaly_report
        )
