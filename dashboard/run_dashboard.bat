@echo off
cd /d "E:\kaggle hackathon google\metacognition-benchmark"
call venv\Scripts\activate
set PYTHONPATH=E:\kaggle hackathon google\metacognition-benchmark
streamlit run dashboard/app.py --server.port 8501
pause
