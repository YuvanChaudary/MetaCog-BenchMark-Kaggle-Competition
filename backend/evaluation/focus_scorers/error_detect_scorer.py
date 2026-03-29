import logging
from typing import Union, List, Any

from backend.evaluation.score_aggregator import FocusScore
from backend.evaluation.focus_scorers.base_scorer import BaseScorer
from backend.evaluation.confidence_parser import parse_confidence_safe

logger = logging.getLogger(__name__)

_raw_flagged = [
    "error", "incorrect", "wrong", "inaccurate",
    "not correct", "mistake", "false", "invalid"
]
_raw_not_flagged = [
    "correct", "accurate", "right", "true",
    "no error", "no mistake", "looks good", "that is right"
]

# Sorted longest-first at module load time securely mapping bounds natively
FLAGGED_PHRASES = sorted(_raw_flagged, key=len, reverse=True)
NOT_FLAGGED_PHRASES = sorted(_raw_not_flagged, key=len, reverse=True)


class ErrorDetectScorer(BaseScorer):
    """
    Evaluates Focus 2 natively identifying error catches across epistemic matrices dynamically without memory accumulation arrays.
    """

    @property
    def focus_area(self) -> str:
        return "error_detection"

    def __init__(self):
        self._n_tasks = 0
        self._detection_sum = 0.0
        self._fp_sum = 0.0
        self._miss_sum = 0.0

    def score(
        self,
        parsed_response: Any,
        ground_truth: Union[str, List[str]],
        task: Any
    ) -> FocusScore:
        
        # STEP 1: Was error planted in this task?
        ep = None
        if isinstance(task, dict):
            ep = task.get("error_planted")
        else:
            ep = getattr(task, "error_planted", None)
            if ep is None and hasattr(task, "model_extra") and task.model_extra:
                ep = task.model_extra.get("error_planted", None)

        if ep is None:
            gts = [ground_truth] if isinstance(ground_truth, str) else ground_truth
            infer_keywords = ["error", "incorrect", "wrong", "false", "not correct"]
            ep_inferred = False
            for gt in gts:
                gt_lower = gt.lower()
                if any(k in gt_lower for k in infer_keywords):
                    ep_inferred = True
                    break
            ep = ep_inferred
            logger.warning(f"error_planted_inferred task_id={getattr(task, 'task_id', 'unknown')}")

        error_planted = bool(ep)

        # STEP 2: Did model flag an error?
        text = getattr(parsed_response, "answer_text", getattr(parsed_response, "extracted_answer", "")).lower()
        
        found_flagged = any(p in text for p in FLAGGED_PHRASES)
        found_not_flagged = any(p in text for p in NOT_FLAGGED_PHRASES)

        if found_flagged and not found_not_flagged:
            model_flagged = True
        elif found_not_flagged and not found_flagged:
            model_flagged = False
        else:
            # AMBIGUOUS: both found OR neither found
            conf_text = getattr(parsed_response, "confidence_text", getattr(parsed_response, "raw_text", ""))
            confidence, _ = parse_confidence_safe(conf_text)
            model_flagged = (confidence < 0.60)
            logger.warning(f"ambiguous_detection task_id={getattr(task, 'task_id', 'unknown')}")

        # STEP 3: Score matrix dynamically
        if model_flagged and error_planted:
            task_score = 100.0    # CORRECT DETECTION
        elif model_flagged and not error_planted:
            task_score = 30.0     # FALSE POSITIVE
        elif not model_flagged and error_planted:
            task_score = 0.0      # MISS
        else:
            task_score = 85.0     # CORRECT REJECTION

        # STEP 4: Update running scalars bounded safely natively holding O(1) space globally
        self._n_tasks += 1
        detection_correct = (model_flagged == error_planted)
        self._detection_sum += float(detection_correct)
        self._fp_sum += float(not error_planted and model_flagged)
        self._miss_sum += float(error_planted and not model_flagged)

        # STEP 5: Dominant failure mappings evaluating rates natively above 0.30 bounds securely
        miss_rate = self._miss_sum / self._n_tasks
        fp_rate = self._fp_sum / self._n_tasks
        
        if miss_rate > 0.30:
            dominant = "failed_error_catch"
        elif fp_rate > 0.30:
            dominant = "excessive_false_positives"
        else:
            dominant = "accurate_error_detection"

        # STEP 6: Output bindings logging directly down BaseScorer template
        self.log_score(
            getattr(task, "task_id", "unknown"),
            task_score,
            self.focus_area,
            {
                "model_flagged": model_flagged,
                "error_planted": error_planted,
                "miss_rate": round(miss_rate, 4),
                "fp_rate": round(fp_rate, 4)
            }
        )

        return FocusScore(
            area=self.focus_area,
            score=task_score,
            n_tasks=self._n_tasks,
            dominant_failure=dominant,
            confidence_interval=(0.0, 0.0) # CI disabled scaling strictly matching scalar array specs natively
        )
