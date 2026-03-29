# e:/kaggle hackathon google/metacognition-benchmark/backend/core/config.py
"""
Central configuration management using Pydantic BaseSettings.
"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings read from environment variables or .env file."""
    MODEL_API_KEY: str = "sk-placeholder"
    DATABASE_BACKEND: Literal["duckdb", "postgres"] = "duckdb"
    DATABASE_URL: str = "./data/metacog.duckdb"
    DATABASE_CONNECTION_POOL: str = "./data/metacog.duckdb"
    TASK_BANK_PATH: str = "./backend/task_registry/tasks"
    FILE_PATH_TASK_BANK: str = "./backend/task_registry/tasks"
    CONFIDENCE_THRESHOLD: float = 0.85
    ADVERSARIAL_PRESSURE_ENABLED: bool = True
    ADVERSARIAL_SAMPLE_RATE: float = 0.30
    EVALUATION_INCLUDE_CONTESTED: bool = False
    JWT_SECRET: str = "dev-secret-key"
    JWT_EXPIRE_MINUTES: int = 480
    MLFLOW_TRACKING_URI: str = "./mlruns"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"
    CALIBRATION_N_BINS: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
