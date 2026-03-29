import os
import random
import hashlib
from datetime import datetime

from backend.core.config import settings
from backend.storage.results_db import ResultsDB, EvaluationResult

FOCUS_AREAS = ["calib", "error_detect", "correction", "certainty"]
DIFFICULTIES = ["easy", "medium", "hard"]
TASKS_PER_COMBO = 50
MODEL_ID = "gpt-4o"

# Target accuracies per focus/difficulty to make the demo look realistic
ACCURACY_TARGET = {
    "calib": {"easy": 0.9, "medium": 0.75, "hard": 0.6},
    "error_detect": {"easy": 0.7, "medium": 0.55, "hard": 0.4},
    "correction": {"easy": 0.8, "medium": 0.65, "hard": 0.5},
    "certainty": {"easy": 0.85, "medium": 0.7, "hard": 0.55},
}


def make_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def generate_results(run_id: str):
    rng = random.Random(42)
    results = []

    for focus in FOCUS_AREAS:
        for difficulty in DIFFICULTIES:
            target_acc = ACCURACY_TARGET[focus][difficulty]
            for idx in range(1, TASKS_PER_COMBO + 1):
                task_id = f"{focus}_{difficulty}_{idx:03d}"
                correct = rng.random() < target_acc
                confidence = max(0.05, min(0.99, rng.normalvariate(target_acc, 0.1)))
                ece_running = max(0.0, 1.0 - target_acc + rng.uniform(-0.05, 0.05))
                brier_running = max(0.0, 1.0 - target_acc + rng.uniform(-0.05, 0.05))

                res = EvaluationResult(
                    run_id=run_id,
                    task_id=task_id,
                    model_id=MODEL_ID,
                    focus_area=focus,
                    difficulty=difficulty,
                    prompt_hash=make_hash(task_id + "_prompt"),
                    answer="stub_answer",
                    ground_truth_hash=make_hash(task_id + "_gt"),
                    confidence=round(confidence, 3),
                    correct=correct,
                    parse_method="synthetic",
                    ece_running=round(ece_running, 3),
                    brier_running=round(brier_running, 3),
                    anomaly_codes=[],
                    metacog_contribution=0.0,
                    latency_ms=rng.uniform(120, 800),
                    timestamp=datetime.utcnow(),
                )
                results.append(res)
    return results


def main():
    run_id = os.environ.get("SEED_RUN_ID", f"run_seed_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}" )
    print(f"Seeding run_id={run_id} with {len(FOCUS_AREAS)*len(DIFFICULTIES)*TASKS_PER_COMBO} rows ...")

    db = ResultsDB(
        backend=settings.DATABASE_BACKEND,
        connection_string=settings.DATABASE_CONNECTION_POOL
    )
    db.initialise()

    results = generate_results(run_id)
    db.write_batch(results)

    summary = db.get_run_summary(run_id)
    print("Done. Summary (per focus):")
    for fa, metrics in summary.items():
        print(f"  {fa}: n={metrics['n_tasks']}, acc={metrics['accuracy']*100:.1f}%")


if __name__ == "__main__":
    main()
