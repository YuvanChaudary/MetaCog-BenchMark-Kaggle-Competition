import os
import json
import time
import logging
from datetime import datetime
from typing import Literal, List, Dict, Any, Tuple
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class EvaluationResult(BaseModel):
    run_id: str
    task_id: str
    model_id: str
    focus_area: str
    difficulty: str = "unknown"
    prompt_hash: str
    answer: str
    ground_truth_hash: str
    confidence: float
    correct: bool
    parse_method: str
    ece_running: float
    brier_running: float
    anomaly_codes: List[str]
    metacog_contribution: float
    latency_ms: float
    timestamp: datetime


class ResultsDB:
    def __init__(
        self,
        backend: Literal["duckdb", "postgres"],
        connection_string: str,
        fallback_path: str = "./data/fallback.jsonl"
    ):
        self.backend = backend
        self.connection_string = connection_string
        self.fallback_path = fallback_path
        self._conn = None

    def initialise(self) -> None:
        if self.backend == "duckdb":
            import duckdb
            db_dir = os.path.dirname(self.connection_string)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            ddl = """
            CREATE TABLE IF NOT EXISTS results (
                run_id VARCHAR,
                task_id VARCHAR,
                model_id VARCHAR,
                focus_area VARCHAR,
                difficulty VARCHAR,
                prompt_hash VARCHAR,
                answer VARCHAR,
                ground_truth_hash VARCHAR,
                confidence DOUBLE,
                correct BOOLEAN,
                parse_method VARCHAR,
                ece_running DOUBLE,
                brier_running DOUBLE,
                anomaly_codes VARCHAR,
                metacog_contribution DOUBLE,
                latency_ms DOUBLE,
                timestamp TIMESTAMP,
                PRIMARY KEY (run_id, task_id)
            )
            """
            with duckdb.connect(self.connection_string) as conn:
                conn.execute(ddl)
            self._conn = "duckdb_managed"

        elif self.backend == "postgres":
            import psycopg2
            try:
                self._conn = psycopg2.connect(self.connection_string)
            except psycopg2.OperationalError as e:
                raise ConnectionError(f"Cannot connect to PostgreSQL at {self.connection_string}. Is it running?") from e
            ddl = """
            CREATE TABLE IF NOT EXISTS results (
                run_id VARCHAR,
                task_id VARCHAR,
                model_id VARCHAR,
                focus_area VARCHAR,
                difficulty VARCHAR,
                prompt_hash VARCHAR,
                answer VARCHAR,
                ground_truth_hash VARCHAR,
                confidence DOUBLE PRECISION,
                correct BOOLEAN,
                parse_method VARCHAR,
                ece_running DOUBLE PRECISION,
                brier_running DOUBLE PRECISION,
                anomaly_codes VARCHAR,
                metacog_contribution DOUBLE PRECISION,
                latency_ms DOUBLE PRECISION,
                timestamp TIMESTAMP,
                PRIMARY KEY (run_id, task_id)
            )
            """
            with self._conn.cursor() as cur:
                cur.execute(ddl)
            self._conn.commit()

    def _get_tuple(self, res: EvaluationResult, is_postgres: bool = False) -> Tuple:
        return (
            res.run_id,
            res.task_id,
            res.model_id,
            res.focus_area,
            res.difficulty,
            res.prompt_hash,
            res.answer,
            res.ground_truth_hash,
            res.confidence,
            res.correct,
            res.parse_method,
            res.ece_running,
            res.brier_running,
            json.dumps(res.anomaly_codes),
            res.metacog_contribution,
            res.latency_ms,
            res.timestamp
        )

    def write_result(self, result: EvaluationResult) -> None:
        data_tuple = self._get_tuple(result, self.backend == "postgres")
        
        if self.backend == "duckdb":
            sql = """
            INSERT OR REPLACE INTO results (
                run_id, task_id, model_id, focus_area, difficulty, prompt_hash,
                answer, ground_truth_hash, confidence, correct, parse_method,
                ece_running, brier_running, anomaly_codes,
                metacog_contribution, latency_ms, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        else:
            sql = """
            INSERT INTO results (
                run_id, task_id, model_id, focus_area, difficulty, prompt_hash,
                answer, ground_truth_hash, confidence, correct, parse_method,
                ece_running, brier_running, anomaly_codes,
                metacog_contribution, latency_ms, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id, task_id) DO UPDATE SET
                model_id = EXCLUDED.model_id,
                focus_area = EXCLUDED.focus_area,
                difficulty = EXCLUDED.difficulty,
                prompt_hash = EXCLUDED.prompt_hash,
                answer = EXCLUDED.answer,
                ground_truth_hash = EXCLUDED.ground_truth_hash,
                confidence = EXCLUDED.confidence,
                correct = EXCLUDED.correct,
                parse_method = EXCLUDED.parse_method,
                ece_running = EXCLUDED.ece_running,
                brier_running = EXCLUDED.brier_running,
                anomaly_codes = EXCLUDED.anomaly_codes,
                metacog_contribution = EXCLUDED.metacog_contribution,
                latency_ms = EXCLUDED.latency_ms,
                timestamp = EXCLUDED.timestamp
            """

        delays = [1, 2, 4]
        for attempt in range(3):
            try:
                if self.backend == "duckdb":
                    import duckdb
                    with duckdb.connect(self.connection_string) as conn:
                        conn.execute(sql, data_tuple)
                else:
                    with self._conn.cursor() as cur:
                        cur.execute(sql, data_tuple)
                    self._conn.commit()
                return
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Storage failure on task_id {result.task_id} after 3 attempts. Exception: {e}")
                    self._write_to_fallback(result)
                    return
                time.sleep(delays[attempt])

    def _write_to_fallback(self, result: EvaluationResult) -> None:
        try:
            fb_dir = os.path.dirname(self.fallback_path)
            if fb_dir:
                os.makedirs(fb_dir, exist_ok=True)
            with open(self.fallback_path, "a", encoding="utf-8") as f:
                f.write(result.model_dump_json() + "\n")
        except Exception as fb_err:
            logger.error(f"FATAL: Database and fallback log failed. {fb_err}")

    def write_batch(self, results: List[EvaluationResult]) -> None:
        if not results:
            return

        cols = [self._get_tuple(r, self.backend == "postgres") for r in results]
        try:
            if self.backend == "duckdb":
                sql = """
                INSERT OR REPLACE INTO results (
                    run_id, task_id, model_id, focus_area, difficulty, prompt_hash,
                    answer, ground_truth_hash, confidence, correct, parse_method,
                    ece_running, brier_running, anomaly_codes,
                    metacog_contribution, latency_ms, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                import duckdb
                with duckdb.connect(self.connection_string) as conn:
                    conn.executemany(sql, cols)
            else:
                import psycopg2.extras
                sql = """
                INSERT INTO results (
                    run_id, task_id, model_id, focus_area, difficulty, prompt_hash,
                    answer, ground_truth_hash, confidence, correct, parse_method,
                    ece_running, brier_running, anomaly_codes,
                    metacog_contribution, latency_ms, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, task_id) DO UPDATE SET
                    model_id = EXCLUDED.model_id,
                    focus_area = EXCLUDED.focus_area,
                    difficulty = EXCLUDED.difficulty,
                    prompt_hash = EXCLUDED.prompt_hash,
                    answer = EXCLUDED.answer,
                    ground_truth_hash = EXCLUDED.ground_truth_hash,
                    confidence = EXCLUDED.confidence,
                    correct = EXCLUDED.correct,
                    parse_method = EXCLUDED.parse_method,
                    ece_running = EXCLUDED.ece_running,
                    brier_running = EXCLUDED.brier_running,
                    anomaly_codes = EXCLUDED.anomaly_codes,
                    metacog_contribution = EXCLUDED.metacog_contribution,
                    latency_ms = EXCLUDED.latency_ms,
                    timestamp = EXCLUDED.timestamp
                """
                with self._conn.cursor() as cur:
                    psycopg2.extras.execute_batch(cur, sql, cols)
                self._conn.commit()
        except Exception:
            for r in results:
                self.write_result(r)

    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        if self.backend == "duckdb":
            sql = """
            SELECT focus_area,
                   COUNT(*) as n_tasks,
                   AVG(confidence) as mean_confidence,
                   AVG(CAST(correct AS INTEGER)) as accuracy,
                   AVG(ece_running) as mean_ece,
                   AVG(brier_running) as mean_brier
            FROM results
            WHERE run_id = ?
            GROUP BY focus_area
            """
            import duckdb
            with duckdb.connect(self.connection_string, read_only=True) as conn:
                cur = conn.execute(sql, [run_id])
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
            summary = {}
            for row in rows:
                d = dict(zip(cols, row))
                fa = d.pop('focus_area')
                summary[fa] = d
            return summary
            
        else:
            sql = """
            SELECT focus_area,
                   COUNT(*) as n_tasks,
                   AVG(confidence) as mean_confidence,
                   AVG(CAST(correct AS INTEGER)) as accuracy,
                   AVG(ece_running) as mean_ece,
                   AVG(brier_running) as mean_brier
            FROM results
            WHERE run_id = %s
            GROUP BY focus_area
            """
            with self._conn.cursor() as cur:
                cur.execute(sql, (run_id,))
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                summary = {}
                for row in rows:
                    d = dict(zip(cols, row))
                    fa = d.pop('focus_area')
                    summary[fa] = d
                return summary

    def close(self) -> None:
        if self._conn is not None and self._conn != "duckdb_managed":
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.initialise()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
