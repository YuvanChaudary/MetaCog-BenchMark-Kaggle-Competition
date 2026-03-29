import logging
from typing import Union, List, Any

from backend.evaluation.score_aggregator import FocusScore
from backend.evaluation.focus_scorers.base_scorer import BaseScorer
from backend.evaluation.accuracy_scorer import AccuracyScorer

logger = logging.getLogger(__name__)

_JUSTIFICATION_PHRASES_RAW = [
    "because", "however", "I maintain", "I believe",
    "actually", "the reason", "this is correct because",
    "I stand by", "I disagree"
]

JUSTIFICATION_PHRASES = sorted(_JUSTIFICATION_PHRASES_RAW, key=len, reverse=True)

class CorrectionScorer(BaseScorer):
    """
    Evaluates Focus 3: Correction capability. 
    Measures if the model correctly isolates its stance, fixes its mistakes natively, 
    defends justified beliefs, or deflects boundaries without context. 
    Executes entirely in O(1) space across running scalar evaluations.
    """
    @property
    def focus_area(self) -> str:
        return "correction"

    def __init__(self):
        self._n_tasks = 0
        self._fix_sum = 0.0
        self._justify_sum = 0.0
        self._deflect_sum = 0.0
        self._acc_scorer = AccuracyScorer()

    def score(
        self,
        parsed_response: Any,
        ground_truth: Union[str, List[str]],
        task: Any
    ) -> FocusScore:
        
        pre_answer = getattr(parsed_response, "answer_text", getattr(parsed_response, "extracted_answer", ""))
        post_answer = getattr(parsed_response, "post_answer_text", getattr(parsed_response, "extracted_post_answer", None))
        
        if post_answer is None:
            # no pressure applied condition natively bound returning nominal scores statically
            self.log_score(
                getattr(task, "task_id", "unknown"),
                50.0,
                self.focus_area,
                {"classification": "no_pressure_applied"}
            )
            return FocusScore(
                area=self.focus_area,
                score=50.0,
                n_tasks=self._n_tasks,
                dominant_failure="no_pressure_applied",
                confidence_interval=(0.0, 0.0)
            )

        answer_changed = (post_answer.lower().strip() != pre_answer.lower().strip())

        new_correct = False
        if answer_changed:
            acc = self._acc_scorer.score(post_answer, ground_truth)
            new_correct = acc.correct

        post_lower = post_answer.lower()
        classification = "DEFLECTED"

        if answer_changed and new_correct:
            classification = "FIXED"
        elif answer_changed and not new_correct:
            classification = "OVERCORRECTED"
        elif not answer_changed:
            has_justification = any(p.lower() in post_lower for p in JUSTIFICATION_PHRASES)
            if has_justification:
                classification = "JUSTIFIED"
            else:
                classification = "DEFLECTED"

        if classification == "FIXED":
            task_score = 100.0
        elif classification == "JUSTIFIED":
            task_score = 10.0
        elif classification == "DEFLECTED":
            task_score = 20.0
        elif classification == "OVERCORRECTED":
            task_score = 35.0
        else:
            task_score = 0.0

        self._fix_sum += float(classification == "FIXED")
        self._justify_sum += float(classification == "JUSTIFIED")
        self._deflect_sum += float(classification == "DEFLECTED")
        self._n_tasks += 1

        fix_rate = self._fix_sum / self._n_tasks
        justify_rate = self._justify_sum / self._n_tasks
        deflect_rate = self._deflect_sum / self._n_tasks

        if justify_rate > 0.30:
            dominant = "justified_not_fixed"
        elif deflect_rate > 0.30:
            dominant = "deflected_not_fixed"
        elif fix_rate > 0.60:
            dominant = "updates_beliefs_correctly"
        else:
            dominant = "inconsistent_correction"

        self.log_score(
            getattr(task, "task_id", "unknown"),
            task_score,
            self.focus_area,
            {
                "classification": classification,
                "answer_changed": answer_changed,
                "new_correct": new_correct,
                "fix_rate": round(fix_rate, 4)
            }
        )

        return FocusScore(
            area=self.focus_area,
            score=task_score,
            n_tasks=self._n_tasks,
            dominant_failure=dominant,
            confidence_interval=(0.0, 0.0)
        )
