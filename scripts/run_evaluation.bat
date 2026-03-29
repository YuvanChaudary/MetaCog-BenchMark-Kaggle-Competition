@echo off
cd /d "E:\kaggle hackathon google\metacognition-benchmark"
call venv\Scripts\activate
set PYTHONPATH=E:\kaggle hackathon google\metacognition-benchmark
echo.
echo  MetaCog Live Evaluation
echo  =======================
echo.
set /p MODEL=Enter model ID (e.g. gpt-4o, ollama/llama3): 
set /p TASKS=Number of tasks (default 20): 
if "%TASKS%"=="" set TASKS=20
set /p FOCUS=Focus area (all/calibration/error_detection/correction/certainty): 
if "%FOCUS%"=="" set FOCUS=all
echo.
python scripts/run_evaluation.py --model %MODEL% --tasks %TASKS% --focus %FOCUS% --verbose
pause
