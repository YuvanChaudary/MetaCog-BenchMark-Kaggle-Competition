import json
import math
import logging
from abc import ABC, abstractmethod
from typing import Union, List, Tuple

logger = logging.getLogger(__name__)

class BaseScorer(ABC):
    """
    Abstract Base Class representing the template signature across all isolated metacognitive focus layers.
    Includes built-in math heuristics for bounds calculation dynamically.
    """
    SCORE_VERSION: str = "1.0.0"

    @property
    @abstractmethod
    def focus_area(self) -> str:
        """Each subclass must return its focus area string natively."""
        pass

    @abstractmethod
    def score(
        self,
        parsed_response,
        ground_truth: Union[str, List[str]],
        task
    ) -> "FocusScore":
        """
        Executes isolated evaluation scoring specific to the subclass focus. O(1) space guarantee bound dynamically across models.
        """
        pass

    def normalise_score(self, raw: float, min_val: float, max_val: float) -> float:
        """
        Condenses unbounded or dynamic internal metric mappings squarely onto the standard 0.0-100.0 grading boundary safely.
        """
        if min_val == max_val:
            return 0.0
            
        result = ((raw - min_val) / (max_val - min_val)) * 100.0
        return max(0.0, min(100.0, result))

    def compute_confidence_interval(self, scores: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """
        Extracts robust structural Wilson score interval distributions from pure binary properties recursively without scipy constraints.
        """
        n = len(scores)
        if n == 0:
            return (0.0, 0.0)
            
        p = sum(scores) / n
        z = 1.96  # statically locked approximation supporting 95% threshold confidence internally
        
        z_sq = z * z
        denominator = 1 + z_sq / n
        
        centre = (p + z_sq / (2 * n)) / denominator
        margin = (z * math.sqrt(p * (1 - p) / n + z_sq / (4 * n * n))) / denominator
        
        lower = max(0.0, centre - margin)
        upper = min(1.0, centre + margin)
        
        return (round(lower, 4), round(upper, 4))

    def log_score(self, task_id: str, score: float, focus_area: str, detail: dict) -> None:
        """
        Emits targeted standard structured payloads appending dynamically loaded component versions for data observability.
        """
        logger.info(json.dumps({
            "event": "focus_score",
            "task_id": task_id,
            "focus_area": focus_area,
            "score": score,
            "version": self.SCORE_VERSION,
            "detail": detail
        }))
