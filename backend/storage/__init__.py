# e:/kaggle hackathon google/metacognition-benchmark/backend/storage/__init__.py
"""
Storage module handling DuckDB/Postgres connections and versioning.
"""
from .results_db import ResultsDB

__all__ = ["ResultsDB"]
