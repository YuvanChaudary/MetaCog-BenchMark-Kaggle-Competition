@echo off
setlocal EnableDelayedExpansion

:: --------------------------------------------------------
:: STEP 0 - SETUP
:: --------------------------------------------------------
cd /d "E:\kaggle hackathon google\metacognition-benchmark"
if %errorlevel% neq 0 (
    echo [FATAL] Failed to cd to project root.
    exit /b 1
)

call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo [FATAL] Failed to activate virtual environment.
    exit /b 1
)

set PYTHONPATH=E:\kaggle hackathon google\metacognition-benchmark

set /a PASS=0
set /a FAIL=0
set "FAIL_LIST="

:: --------------------------------------------------------
:: STEP 1 - MODULE IMPORT CHECKS
:: --------------------------------------------------------
echo --------------------------------------------------------
echo STEP 1: MODULE IMPORT CHECKS
echo --------------------------------------------------------

call :check_import backend.task_registry.task_schema TaskObject task_schema
call :check_import backend.task_registry.task_loader TaskLoader task_loader
call :check_import backend.evaluation.confidence_parser parse_confidence_safe confidence_parser
call :check_import backend.evaluation.calibration_engine CalibrationEngine calibration_engine
call :check_import backend.evaluation.accuracy_scorer AccuracyScorer accuracy_scorer
call :check_import backend.evaluation.anomaly_detector AnomalyDetector anomaly_detector
call :check_import backend.evaluation.score_aggregator MetaCogAggregator score_aggregator
call :check_import backend.storage.results_db ResultsDB results_db
call :check_import backend.evaluation.focus_scorers.base_scorer BaseScorer base_scorer
call :check_import backend.evaluation.focus_scorers.calib_scorer CalibScorer calib_scorer
call :check_import backend.evaluation.focus_scorers.error_detect_scorer ErrorDetectScorer error_detect_scorer
call :check_import backend.evaluation.focus_scorers.correction_scorer CorrectionScorer correction_scorer
call :check_import backend.evaluation.focus_scorers.certainty_scorer CertaintyScorer certainty_scorer

:: --------------------------------------------------------
:: STEP 2 - PYTEST UNIT TESTS
:: --------------------------------------------------------
echo --------------------------------------------------------
echo STEP 2: PYTEST UNIT TESTS
echo --------------------------------------------------------
pytest tests\unit\ -v --tb=short
if %errorlevel% equ 0 (
    echo [PASS] All unit tests passed
    set /a PASS+=1
) else (
    echo [FAIL] pytest unit tests failed
    set /a FAIL+=1
    set "FAIL_LIST=!FAIL_LIST! unit_tests"
)

:: --------------------------------------------------------
:: STEP 3 - PYTEST INTEGRATION TESTS
:: --------------------------------------------------------
echo --------------------------------------------------------
echo STEP 3: PYTEST INTEGRATION TESTS
echo --------------------------------------------------------
if exist tests\integration\ (
    pytest tests\integration\ -v --tb=short
    if !errorlevel! equ 0 (
        echo [PASS] All integration tests passed
        set /a PASS+=1
    ) else (
        echo [FAIL] pytest integration tests failed
        set /a FAIL+=1
        set "FAIL_LIST=!FAIL_LIST! integration_tests"
    )
) else (
    echo [SKIP] No integration tests folder found yet.
)

:: --------------------------------------------------------
:: STEP 4 - FASTAPI HEALTH CHECK
:: --------------------------------------------------------
echo --------------------------------------------------------
echo STEP 4: FASTAPI HEALTH CHECK
echo --------------------------------------------------------
start /b "" uvicorn backend.api.main:app --port 8001
timeout /t 4 /nobreak > nul

curl -s http://localhost:8001/health > health_temp.txt
findstr /i "ok" health_temp.txt > nul
if !errorlevel! equ 0 (
    echo [PASS] FastAPI health check passed
    set /a PASS+=1
) else (
    echo [FAIL] FastAPI health check failed
    set /a FAIL+=1
    set "FAIL_LIST=!FAIL_LIST! fastapi_health"
)

taskkill /f /im uvicorn.exe > nul 2>&1
if exist health_temp.txt del health_temp.txt

:: --------------------------------------------------------
:: FINAL REPORT
:: --------------------------------------------------------
echo --------------------------------------------------------
echo FINAL REPORT
echo --------------------------------------------------------
echo Total PASS count : !PASS!
echo Total FAIL count : !FAIL!

if !FAIL! equ 0 (
    echo STATUS: ALL CHECKS PASSED - Ready to build next module.
) else (
    echo Failed checks: !FAIL_LIST!
    echo STATUS: !FAIL! CHECK^(S^) FAILED - Paste this output to Claude for fixes.
)

pause
exit /b 0

:: --------------------------------------------------------
:: SUBROUTINES
:: --------------------------------------------------------
:check_import
set "module=%~1"
set "class_name=%~2"
set "label=%~3"

python -c "from %module% import %class_name%" > nul 2>&1
if %errorlevel% equ 0 (
    echo [PASS] %label%
    set /a PASS+=1
) else (
    echo [FAIL] %label%
    set /a FAIL+=1
    set "FAIL_LIST=!FAIL_LIST! %label%"
)
exit /b 0
