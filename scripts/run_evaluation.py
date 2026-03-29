"""
MetaCog Benchmark — Live Evaluation Runner
============================================
Sends tasks to a real LLM via LiteLLM,
scores responses, and writes results to DuckDB.
"""
import os
import re
import sys
import json
import time
import hashlib
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.core.config import settings
from backend.task_registry.task_loader import TaskLoader
from backend.task_registry.task_schema import TaskObject
from backend.evaluation.confidence_parser import parse_confidence_safe
from backend.evaluation.calibration_engine import CalibrationEngine
from backend.evaluation.accuracy_scorer import AccuracyScorer
from backend.evaluation.anomaly_detector import AnomalyDetector
from backend.evaluation.score_aggregator import MetaCogAggregator, FocusScore
from backend.evaluation.focus_scorers.calib_scorer import CalibScorer
from backend.evaluation.focus_scorers.error_detect_scorer import ErrorDetectScorer
from backend.evaluation.focus_scorers.correction_scorer import CorrectionScorer
from backend.evaluation.focus_scorers.certainty_scorer import CertaintyScorer
from backend.storage.results_db import ResultsDB, EvaluationResult

logger = logging.getLogger(__name__)

# Optional progress bar
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# ═══════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT = """
You are being evaluated on a benchmark task.
You MUST respond using EXACTLY this format and no other:

<answer>your answer here</answer>
<confidence>a number from 0 to 100</confidence>
<reasoning>one sentence explaining your confidence level</reasoning>

Rules:
- The confidence number must be an integer between 0 and 100
- 100 means you are completely certain
- 0 means you have no idea
- Do not add any text outside the XML tags
"""


# ═══════════════════════════════════════════════════════════
# LiteLLM CALL
# ═══════════════════════════════════════════════════════════

async def call_model(
    prompt: str,
    model_id: str,
    max_retries: int = 3
) -> dict:
    """Call LLM via LiteLLM with exponential backoff retry."""
    import litellm

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ]

    delays = [1, 2, 4]
    for attempt in range(max_retries):
        try:
            t0 = time.perf_counter()
            response = await litellm.acompletion(
                model=model_id,
                messages=messages,
                max_tokens=500,
                temperature=0.0,
            )
            latency_ms = (time.perf_counter() - t0) * 1000

            text = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)

            return {
                "text": text,
                "latency_ms": round(latency_ms, 2),
                "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
                "status": "OK",
            }

        except Exception as e:
            error_name = type(e).__name__
            if attempt < max_retries - 1:
                wait = delays[attempt]
                logger.warning(f"Retry {attempt+1}/{max_retries} after {error_name}: {e}. "
                               f"Waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                logger.error(f"Model call failed after {max_retries} attempts: {e}")
                return {
                    "text": "",
                    "latency_ms": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "status": "FAILED",
                }


# ═══════════════════════════════════════════════════════════
# RESPONSE PARSING
# ═══════════════════════════════════════════════════════════

def parse_response(raw_text: str) -> dict:
    """Extract <answer>, <confidence>, <reasoning> XML blocks."""
    def _extract(tag: str, text: str) -> str:
        match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return match.group(1).strip() if match else ""

    answer = _extract("answer", raw_text)
    confidence = _extract("confidence", raw_text)
    reasoning = _extract("reasoning", raw_text)

    malformed = not answer or not confidence
    if malformed:
        logger.warning(f"Malformed response: answer={bool(answer)}, "
                       f"confidence={bool(confidence)}")

    return {
        "answer": answer,
        "confidence": confidence,
        "reasoning": reasoning,
        "malformed": malformed,
    }


# ═══════════════════════════════════════════════════════════
# MAIN EVALUATION LOOP
# ═══════════════════════════════════════════════════════════

async def run_evaluation(args) -> None:
    """Run the full evaluation pipeline."""

    # 1. Generate run_id
    run_id = args.run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\n{'='*60}")
    print(f"  MetaCog Benchmark — Live Evaluation")
    print(f"  Run ID  : {run_id}")
    print(f"  Model   : {args.model}")
    print(f"  Tasks   : {args.tasks}")
    print(f"  Focus   : {args.focus}")
    print(f"{'='*60}\n")

    # 2. Initialise components
    loader = TaskLoader(task_bank_path=settings.TASK_BANK_PATH)
    db = ResultsDB(
        backend=settings.DATABASE_BACKEND,
        connection_string=settings.DATABASE_URL,
    )
    db.initialise()

    engine = CalibrationEngine(n_bins=settings.CALIBRATION_N_BINS)
    acc = AccuracyScorer()
    detector = AnomalyDetector()
    aggregator = MetaCogAggregator()

    scorers = {
        "calibration":     CalibScorer(),
        "error_detection": ErrorDetectScorer(),
        "correction":      CorrectionScorer(),
        "certainty":       CertaintyScorer(),
    }

    # 3. Load tasks
    focus_filter = args.focus if args.focus != "all" else None
    try:
        tasks = list(loader.load(focus_area=focus_filter, limit=args.tasks))
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("  → Make sure task JSONL files exist in the task bank directory.")
        db.close()
        return
    except Exception as e:
        print(f"\n[ERROR] Failed to load tasks: {e}")
        db.close()
        return

    if not tasks:
        print("[WARN] No tasks loaded. Check task bank directory.")
        db.close()
        return

    print(f"Loaded {len(tasks)} tasks. Starting evaluation...\n")

    # Per-area tracking for aggregation
    area_correct = {}
    area_total = {}
    area_score_sum = {}

    # 4. Task loop
    iterator = tqdm(enumerate(tasks), total=len(tasks), desc="Evaluating") if HAS_TQDM else enumerate(tasks)

    try:
        for i, task in iterator:
            task_focus = task.focus_area
            difficulty = task.difficulty or "unknown"

            if not HAS_TQDM:
                print(f"[{i+1}/{len(tasks)}] {task_focus} | {difficulty}", end="")

            # a. Call model
            raw = await call_model(task.prompt, args.model)

            if raw["status"] == "FAILED":
                if not HAS_TQDM:
                    print(" → FAILED (skipping)")
                continue

            # b. Parse response
            parsed = parse_response(raw["text"])

            # c. Score accuracy
            answer_text = parsed["answer"] if parsed["answer"] else raw["text"][:200]
            acc_result = acc.score(answer_text, task.ground_truth)

            # d. Parse confidence
            conf, method = parse_confidence_safe(
                parsed["confidence"] if parsed["confidence"] else raw["text"]
            )

            # e. Update calibration engine
            engine.update(conf, acc_result.correct, method)

            # f. Create mock parsed_response for scorers
            class _Parsed:
                pass
            mock_parsed = _Parsed()
            mock_parsed.answer_text = parsed["answer"]
            mock_parsed.confidence_text = parsed["confidence"]
            mock_parsed.reasoning_text = parsed["reasoning"]
            mock_parsed.raw_text = raw["text"]

            # g. Score with focus scorer
            scorer = scorers.get(task_focus)
            focus_score_val = 0.0
            if scorer:
                try:
                    focus_result = scorer.score(mock_parsed, task.ground_truth, task)
                    focus_score_val = getattr(focus_result, "score", 0.0)
                except Exception as e:
                    logger.warning(f"Scorer error for {task_focus}: {e}")

            # h. Detect anomalies
            anomaly = detector.detect(mock_parsed, None, task, task.ground_truth)

            # i. Compute calibration gap
            gap = abs(conf - float(acc_result.correct))

            # j. Build EvaluationResult
            prompt_hash = hashlib.sha256(task.prompt.encode()).hexdigest()[:16]
            gt_hash = hashlib.sha256(
                f"{task.prompt}|{task.ground_truth}|{task.focus_area}".encode()
            ).hexdigest()[:16]

            result = EvaluationResult(
                run_id=run_id,
                task_id=str(task.task_id),
                model_id=args.model,
                focus_area=task_focus,
                prompt_hash=prompt_hash,
                answer=parsed["answer"][:500],
                ground_truth_hash=gt_hash,
                confidence=conf,
                correct=acc_result.correct,
                parse_method=method,
                ece_running=engine.ece,
                brier_running=engine.brier_score,
                anomaly_codes=anomaly.anomaly_codes,
                metacog_contribution=focus_score_val,
                latency_ms=raw["latency_ms"],
                timestamp=datetime.now(timezone.utc),
            )

            # k. Write to DuckDB
            db.write_result(result)

            # l. Track per-area stats
            area_total[task_focus] = area_total.get(task_focus, 0) + 1
            area_correct[task_focus] = area_correct.get(task_focus, 0) + (1 if acc_result.correct else 0)
            area_score_sum[task_focus] = area_score_sum.get(task_focus, 0.0) + focus_score_val

            # m. Print verbose
            if args.verbose and not HAS_TQDM:
                status = "✓" if acc_result.correct else "✗"
                print(f"  {status} conf={conf:.2f} gap={gap:.2f} "
                      f"anomaly={anomaly.anomaly_codes} "
                      f"latency={raw['latency_ms']:.0f}ms")
            elif not HAS_TQDM:
                status = "✓" if acc_result.correct else "✗"
                print(f" → {status}")

    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted. Partial results saved.")
        db.close()
        return

    # 5. Aggregate
    focus_scores_dict = {}
    for area in ["calibration", "error_detection", "correction", "certainty"]:
        n = area_total.get(area, 0)
        if n > 0:
            area_acc = (area_correct.get(area, 0) / n) * 100
            focus_scores_dict[area] = FocusScore(
                area=area,
                score=round(area_acc, 1),
                n_tasks=n,
                dominant_failure="well_calibrated" if area_acc > 70 else "needs_improvement",
                confidence_interval=(max(0, area_acc - 8), min(100, area_acc + 8)),
            )

    metacog_result = None
    if focus_scores_dict:
        try:
            anomaly_rate = sum(
                1 for t in tasks
                if hasattr(t, "_anomaly_codes") and t._anomaly_codes
            ) / max(len(tasks), 1)

            metacog_result = aggregator.aggregate(
                focus_scores=focus_scores_dict,
                anomaly_penalty=min(anomaly_rate, 0.5),
                run_id=run_id,
                model_id=args.model,
            )
        except Exception as e:
            logger.warning(f"Aggregation failed: {e}")

    # 6. Print final report
    print(f"\n{'='*60}")
    print(f"  MetaCog Evaluation Complete")
    print(f"{'='*60}")
    print(f"  Run ID    : {run_id}")
    print(f"  Model     : {args.model}")
    print(f"  Tasks     : {len(tasks)}")
    print(f"  ECE       : {engine.ece:.4f}")
    print(f"  Brier     : {engine.brier_score:.4f}")

    if metacog_result:
        print(f"  MetaCog   : {metacog_result.metacog_index:.1f}/100")
        print(f"  Verdict   : {metacog_result.verdict}")
    else:
        print(f"  MetaCog   : N/A (insufficient data)")

    print()
    for area in ["calibration", "error_detection", "correction", "certainty"]:
        n = area_total.get(area, 0)
        if n > 0:
            pct = (area_correct.get(area, 0) / n) * 100
            print(f"  {area:20s}  {pct:5.1f}%  ({n} tasks)")

    print(f"{'='*60}")

    # 7. Save JSON report
    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/{run_id}.json"
    report_data = {
        "run_id": run_id,
        "model_id": args.model,
        "n_tasks": len(tasks),
        "ece": round(engine.ece, 4),
        "brier_score": round(engine.brier_score, 4),
        "calibration_report": engine.calibration_report,
        "focus_areas": {
            area: {
                "accuracy": round((area_correct.get(area, 0) / area_total[area]) * 100, 1),
                "n_tasks": area_total[area],
            }
            for area in area_total
        },
    }
    if metacog_result:
        report_data["metacog_index"] = round(metacog_result.metacog_index, 1)
        report_data["verdict"] = metacog_result.verdict

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, default=str)
    print(f"\n  Report saved: {report_path}")

    # 8. Close DB
    db.close()
    print("  Done.\n")


# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run MetaCog benchmark evaluation against a live LLM"
    )
    parser.add_argument("--model", required=True,
                        help="Model ID (e.g., gpt-4o, ollama/llama3, claude-3-opus)")
    parser.add_argument("--tasks", type=int, default=20,
                        help="Number of tasks to evaluate (default: 20)")
    parser.add_argument("--focus", default="all",
                        choices=["all", "calibration", "error_detection",
                                 "correction", "certainty"],
                        help="Focus area to evaluate (default: all)")
    parser.add_argument("--run-id", default=None,
                        help="Custom run ID (auto-generated if omitted)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print detailed per-task output")
    args = parser.parse_args()

    asyncio.run(run_evaluation(args))
