cd /d "E:\kaggle hackathon google\metacognition-benchmark"
call venv\Scripts\activate.bat
set PYTHONPATH=E:\kaggle hackathon google\metacognition-benchmark
python -c "from backend.evaluation.score_aggregator import MetaCogAggregator; print('OK')"
python -c "from backend.task_registry.task_schema import TaskObject; print('OK')"
python -c "from backend.evaluation.confidence_parser import parse_confidence_safe; print('OK')"
pytest tests/unit/ -v --tb=short
