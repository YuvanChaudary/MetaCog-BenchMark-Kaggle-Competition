import logging
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class _Bin:
    sum_conf: float = 0.0
    sum_acc: float = 0.0
    count: int = 0

    @property
    def avg_conf(self) -> float:
        return self.sum_conf / self.count if self.count > 0 else 0.0

    @property
    def avg_acc(self) -> float:
        return self.sum_acc / self.count if self.count > 0 else 0.0

    @property
    def calibration_gap(self) -> float:
        return self.avg_conf - self.avg_acc


class CalibrationEngine:
    """
    Space complexity is O(1) per evaluation event.
    self.bins is allocated once at __init__ with fixed length
    n_bins and never grows. Three scalar accumulators
    (brier_sum, n_total, overconf_count) are updated in-place.
    No list of (confidence, correct) pairs is ever stored.
    Memory usage is constant regardless of n evaluations.
    """

    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins
        self.bins = [_Bin() for _ in range(n_bins)]
        self._brier_sum: float = 0.0
        self._n_total: int = 0
        self._overconf_count: int = 0
        self._underconf_count: int = 0
        self._excluded_count: int = 0

    def update(self, confidence: float, correct: bool, parse_method: str = "NUMERIC") -> None:
        if parse_method == "DEFAULT_FALLBACK":
            self._excluded_count += 1
            return

        self._n_total += 1
        
        bin_idx = min(int(confidence * self.n_bins), self.n_bins - 1)
        b = self.bins[bin_idx]
        
        b.sum_conf += confidence
        acc_value = 1.0 if correct else 0.0
        b.sum_acc += acc_value
        b.count += 1

        self._brier_sum += (confidence - acc_value) ** 2

        if confidence > 0.70 and not correct:
            self._overconf_count += 1

        if confidence < 0.40 and correct:
            self._underconf_count += 1

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(json.dumps({
                "event": "calib_update",
                "bin": bin_idx,
                "conf": confidence,
                "correct": correct,
                "gap": b.calibration_gap,
                "running_ece": self.ece
            }))

    @property
    def ece(self) -> float:
        if self._n_total == 0:
            return 0.0
        return sum(
            (b.count / self._n_total) * abs(b.calibration_gap)
            for b in self.bins if b.count > 0
        )

    @property
    def brier_score(self) -> float:
        if self._n_total == 0:
            return 0.0
        return self._brier_sum / self._n_total

    @property
    def overconfidence_rate(self) -> float:
        if self._n_total == 0:
            return 0.0
        return self._overconf_count / self._n_total

    @property
    def underconfidence_rate(self) -> float:
        if self._n_total == 0:
            return 0.0
        return self._underconf_count / self._n_total

    @property
    def n_total(self) -> int:
        return self._n_total

    @property
    def calibration_report(self) -> dict:
        return {
            "ece": round(self.ece, 4),
            "brier_score": round(self.brier_score, 4),
            "overconfidence_rate": round(self.overconfidence_rate, 4),
            "underconfidence_rate": round(self.underconfidence_rate, 4),
            "n_total": self._n_total,
            "n_excluded_fallback": self._excluded_count,
            "bin_data": [
                {
                    "bin_lower": i / self.n_bins,
                    "bin_upper": (i + 1) / self.n_bins,
                    "mean_conf": round(b.avg_conf, 4),
                    "frac_correct": round(b.avg_acc, 4),
                    "count": b.count,
                    "calibration_gap": round(b.calibration_gap, 4)
                }
                for i, b in enumerate(self.bins) if b.count > 0
            ]
        }

    def reset(self) -> None:
        self.bins = [_Bin() for _ in range(self.n_bins)]
        self._brier_sum = 0.0
        self._n_total = 0
        self._overconf_count = 0
        self._underconf_count = 0
        self._excluded_count = 0
