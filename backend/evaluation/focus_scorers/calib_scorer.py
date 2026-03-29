import logging
from typing import Union, List, Any, Dict

from backend.evaluation.score_aggregator import FocusScore
from backend.evaluation.focus_scorers.base_scorer import BaseScorer
from backend.evaluation.calibration_engine import CalibrationEngine
from backend.evaluation.accuracy_scorer import AccuracyScorer
from backend.evaluation.confidence_parser import parse_confidence_safe

logger = logging.getLogger(__name__)

class CalibScorer(BaseScorer):
    """
    Evaluates metacognitive calibration natively isolating objective confidence gaps without memory accumulation.
    """
    
    def __init__(self, n_bins: int = 10, similarity_threshold: float = 0.85):
        self._engine = CalibrationEngine(n_bins=n_bins)
        self._acc = AccuracyScorer(similarity_threshold)
        self._n_tasks = 0
        self._score_history: List[float] = []

    @property
    def focus_area(self) -> str:
        return "calibration"

    def score(
        self,
        parsed_response: Any,
        ground_truth: Union[str, List[str]],
        task: Any
    ) -> FocusScore:
        
        # STEP 1: accuracy
        ans_text = getattr(parsed_response, "answer_text", getattr(parsed_response, "extracted_answer", ""))
        acc_result = self._acc.score(ans_text, ground_truth)
        correct = acc_result.correct

        # STEP 2: confidence extraction natively bypassing exceptions
        conf_text = getattr(parsed_response, "confidence_text", getattr(parsed_response, "raw_text", ""))
        confidence, parse_method = parse_confidence_safe(conf_text)

        # STEP 3: update calibration engine O(1) properties strictly inline
        self._engine.update(confidence, correct, parse_method)

        # STEP 4: absolute distance projection securely normalized onto 0.0 - 100.0 gradients
        calibration_gap = abs(confidence - float(correct))
        task_score = max(0.0, 100.0 - (calibration_gap * 100.0))

        # STEP 5: structured boundary flags natively mapping explicit margins
        if correct is False and confidence > 0.80:
            flag = "OVERCONFIDENCE"
        elif correct is True and confidence < 0.20:
            flag = "UNDERCONFIDENCE"
        else:
            flag = "NORMAL"

        # STEP 6: dominant failure projections extracted structurally over aggregate threshold rates
        if self._engine.overconfidence_rate > 0.30:
            dominant = "overconfident_when_wrong"
        elif self._engine.underconfidence_rate > 0.30:
            dominant = "underconfident_when_right"
        else:
            dominant = "well_calibrated"

        # STEP 7: counters mapping history array bounded natively at max 1k bounds scaling
        self._n_tasks += 1
        if len(self._score_history) < 1000:
            self._score_history.append(task_score / 100.0)

        # STEP 8: recursive base generator binomial approximations natively scaling
        ci = self.compute_confidence_interval(self._score_history)

        # STEP 9: log JSON events mapped dynamically 
        self.log_score(
            getattr(task, "task_id", "unknown"),
            task_score,
            self.focus_area,
            {
                "flag": flag,
                "confidence": confidence,
                "correct": correct,
                "parse_method": parse_method,
                "running_ece": self._engine.ece
            }
        )

        return FocusScore(
            area=self.focus_area,
            score=task_score,
            n_tasks=self._n_tasks,
            dominant_failure=dominant,
            confidence_interval=ci
        )

    def get_run_summary(self) -> Dict[str, Any]:
        """Provides natively isolated summaries wrapped strictly merging engine reports cleanly."""
        report = self._engine.calibration_report
        report["n_tasks"] = self._n_tasks
        return report
