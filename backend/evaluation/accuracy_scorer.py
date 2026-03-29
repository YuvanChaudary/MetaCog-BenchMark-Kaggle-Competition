import re
import json
import logging
import collections
from typing import Literal, Union, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AccuracyResult(BaseModel):
    correct: bool
    match_type: Literal["EXACT", "CONTAINED", "SEMANTIC", "NO_MATCH"]
    similarity: Optional[float]
    answer_normalised: str
    gt_normalised: Union[str, List[str]]

# Module-level singletons caching the Transformer explicitly once for benchmark execution
_model = None
_gt_cache = collections.OrderedDict()
_GT_CACHE_MAX = 1000

class AccuracyScorer:
    """Evaluates raw answer accuracy across tiered literal, substring, and semantic stages."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def _normalise(text: str) -> str:
        """Strips casing, punctuation, and extraneous spacing natively in bounded constant time."""
        # 1. strip and lower
        text = text.strip().lower()
        # 2. remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        # 3. collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        # 4. strip again
        return text.strip()

    def score(self, answer: str, ground_truth: Union[str, List[str]]) -> AccuracyResult:
        if not answer.strip():
            logger.warning("empty_answer")
            return AccuracyResult(
                correct=False,
                match_type="NO_MATCH",
                similarity=None,
                answer_normalised="",
                gt_normalised=ground_truth
            )

        # 1. Normalise answer and GTs
        ans_norm = self._normalise(answer)
        gts = [ground_truth] if isinstance(ground_truth, str) else ground_truth
        gt_norms = [self._normalise(gt) for gt in gts]

        # 2. EXACT
        if any(ans_norm == gt_norm for gt_norm in gt_norms):
            return AccuracyResult(
                correct=True,
                match_type="EXACT",
                similarity=None,
                answer_normalised=ans_norm,
                gt_normalised=gt_norms if isinstance(ground_truth, list) else gt_norms[0]
            )

        # 3. CONTAINED
        if any(gt_norm in ans_norm for gt_norm in gt_norms):
            return AccuracyResult(
                correct=True,
                match_type="CONTAINED",
                similarity=None,
                answer_normalised=ans_norm,
                gt_normalised=gt_norms if isinstance(ground_truth, list) else gt_norms[0]
            )

        # 4. SEMANTIC
        global _model, _gt_cache, _GT_CACHE_MAX

        if _model is None:
            from sentence_transformers import SentenceTransformer
            # Lazily load underlying transformers model exclusively if a baseline semantic check triggers
            _model = SentenceTransformer("all-MiniLM-L6-v2")

        from sentence_transformers import util

        ans_emb = _model.encode(ans_norm, convert_to_tensor=True)
        max_similarity = -1.0

        for gt_norm in gt_norms:
            # OrderedDict acts as LRU cache explicitly mapped against _GT_CACHE_MAX capacity bounds
            if gt_norm in _gt_cache:
                gt_emb = _gt_cache[gt_norm]
                _gt_cache.move_to_end(gt_norm)
            else:
                gt_emb = _model.encode(gt_norm, convert_to_tensor=True)
                _gt_cache[gt_norm] = gt_emb
                if len(_gt_cache) > _GT_CACHE_MAX:
                    _gt_cache.popitem(last=False)

            sim = util.cos_sim(ans_emb, gt_emb).item()
            if sim > max_similarity:
                max_similarity = sim

        match_result = "NO_MATCH"
        correct_state = False

        if max_similarity >= self.similarity_threshold:
            correct_state = True
            match_result = "SEMANTIC"
            logger.info(json.dumps({
                "event": "semantic_match",
                "similarity": max_similarity,
                "match_type": match_result,
                "answer_preview": answer[:40]
            }))
        elif 0.50 <= max_similarity < self.similarity_threshold:
            logger.warning(json.dumps({
                "event": "borderline_similarity",
                "similarity": max_similarity
            }))

        return AccuracyResult(
            correct=correct_state,
            match_type=match_result, # type: ignore
            similarity=max_similarity,
            answer_normalised=ans_norm,
            gt_normalised=gt_norms if isinstance(ground_truth, list) else gt_norms[0]
        )
