import re
import json
import logging
from typing import Literal, Tuple, Dict, Optional

ParseMethod = Literal[
    "NUMERIC", "PERCENTAGE", "VERBAL_MAP", "SENTIMENT", "DEFAULT_FALLBACK"
]

logger = logging.getLogger(__name__)

VERBAL_MAP: Dict[str, float] = {
    "absolutely certain":  0.97,
    "completely certain":  0.96,
    "very confident":      0.90,
    "highly confident":    0.88,
    "fairly confident":    0.70,
    "somewhat confident":  0.55,
    "not very confident":  0.35,
    "not confident":       0.20,
    "very uncertain":      0.15,
    "definitely":          0.92,
    "certainly":           0.91,
    "probably":            0.68,
    "likely":              0.65,
    "possibly":            0.45,
    "unlikely":            0.28,
    "unsure":              0.50,
    "I don't know":        0.10,
    "no idea":             0.10,
    "certain":             0.92,
    "confident":           0.75
}

# Module-level constants evaluated once at import
_NUMERIC_RE = re.compile(r'\b(\d+(?:\.\d+)?)\b')
_PCT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')
_SORTED_HEDGE = sorted(VERBAL_MAP.items(), key=lambda x: -len(x[0]))


def _log_parse(method: ParseMethod, text: str, score: float) -> None:
    """Consistently log structured parsing outcomes."""
    logger.info(json.dumps({
        "event": "confidence_parsed",
        "method": method,
        "input_preview": text[:30],
        "score": score
    }))


def parse_confidence(
    confidence_text: str,
    verbal_map: Optional[Dict[str, float]] = None
) -> Tuple[float, ParseMethod]:
    """
    Evaluates confidence heuristics sequentially, falling back 
    through 5 strict resolution tiers.
    """
    if not confidence_text:
        raise ValueError("confidence_text cannot be empty")

    text_lower = confidence_text.lower()

    # Locate first matches for Tier 1 and Tier 2 validations
    num_match = next(_NUMERIC_RE.finditer(confidence_text), None)
    pct_match = next(_PCT_RE.finditer(confidence_text), None)

    # Edge Case: 'I am 100% sure' -> prevent Tier 1 from hijacking '100'
    if num_match and pct_match and num_match.start(1) == pct_match.start(1):
        num_match = None

    # TIER 1 — Direct numeric
    if num_match:
        val = float(num_match.group(1))
        if val > 1.0:
            val = val / 100.0
        score = max(0.0, min(1.0, val))
        _log_parse("NUMERIC", confidence_text, score)
        return score, "NUMERIC"

    # TIER 2 — Percentage string
    if pct_match:
        # Edge Case check: negation within 5 preceding tokens
        prefix = confidence_text[:pct_match.start()]
        tokens = [t.lower() for t in prefix.replace('\n', ' ').split() if t]
        
        if "not" not in tokens[-5:]:
            val = float(pct_match.group(1))
            score = max(0.0, min(1.0, val / 100.0))
            _log_parse("PERCENTAGE", confidence_text, score)
            return score, "PERCENTAGE"

    # TIER 3 — Verbal hedge map
    v_map = verbal_map if verbal_map is not None else VERBAL_MAP
    if verbal_map is not None:
        sorted_hedge = sorted(v_map.items(), key=lambda x: -len(x[0]))
    else:
        sorted_hedge = _SORTED_HEDGE

    for phrase, val in sorted_hedge:
        if phrase.lower() in text_lower:
            score = max(0.0, min(1.0, val))
            _log_parse("VERBAL_MAP", confidence_text, score)
            return score, "VERBAL_MAP"

    # TIER 4 — TextBlob sentiment polarity
    try:
        from textblob import TextBlob
        blob = TextBlob(confidence_text)
        polarity = blob.sentiment.polarity
        score = 0.10 + (polarity + 1.0) / 2.0 * 0.80
        score = max(0.0, min(1.0, score))
        _log_parse("SENTIMENT", confidence_text, score)
        return score, "SENTIMENT"
    except ImportError:
        # TIER 5 fallback applies if textblob is not installed or import fails
        pass

    # TIER 5 — Default fallback
    score = 0.50
    _log_parse("DEFAULT_FALLBACK", confidence_text, score)
    return score, "DEFAULT_FALLBACK"


def parse_confidence_safe(text: Optional[str]) -> Tuple[float, ParseMethod]:
    """Safe wrapper eliminating exception raisings during parsing."""
    if not text:
        return 0.50, "DEFAULT_FALLBACK"
    try:
        return parse_confidence(text)
    except Exception:
        return 0.50, "DEFAULT_FALLBACK"
