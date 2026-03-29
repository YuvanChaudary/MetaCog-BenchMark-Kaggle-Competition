# e:/kaggle hackathon google/metacognition-benchmark/README.md
# Metacognition Benchmark

A production-grade AI metacognition benchmark framework evaluating AI models across four focus areas: **calibration**, **error detection**, **correction**, and **certainty**.

## 🎯 Features
- **FastAPI Backend**: High-performance async API with automatic documentation
- **Streamlit Dashboard**: Real-time visualization and interactive monitoring
- **O(1) Space Complexity**: Generator-based task loading and streaming evaluation
- **Modular Pipeline**: Independent evaluators for specialized metacognition tests
- **Storage Flexibility**: DuckDB for development, PostgreSQL for production
- **Comprehensive Testing**: Unit and integration tests for quality assurance

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ installed
- Windows Command Prompt (cmd) or PowerShell

### Installation
1. Navigate to project directory:
   ```cmd
   cd "e:\kaggle hackathon google\metacognition-benchmark"
   ```

2. Create virtual environment (first time only):
   ```cmd
   python -m venv .venv
   ```

3. Activate virtual environment:
   ```cmd
   .venv\Scripts\activate.bat
   ```

4. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

## 📋 Running the Project

### Option 1: Backend Only (API)
```cmd
cd "e:\kaggle hackathon google\metacognition-benchmark" && .venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8001
```
Access API at: http://localhost:8001/docs

### Option 2: Frontend Only (Dashboard)
```cmd
cd "e:\kaggle hackathon google\metacognition-benchmark" && .venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501
```
Access Dashboard at: http://localhost:8501

### Option 3: Both Backend & Frontend (Recommended)
Open **2 separate CMD windows**:

**Window 1 - Backend:**
```cmd
cd "e:\kaggle hackathon google\metacognition-benchmark" && .venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8001
```

**Window 2 - Frontend:**
```cmd
cd "e:\kaggle hackathon google\metacognition-benchmark" && .venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501
```

## 🌐 Access Points
| Component | URL | Purpose |
|-----------|-----|---------|
| API Documentation | http://localhost:8001/docs | Interactive API testing |
| API Alternative Docs | http://localhost:8001/redoc | RESTful documentation |
| Health Check | http://localhost:8001/health | Server status |
| Dashboard | http://localhost:8501 | Live metrics & visualization |

## 📚 Available API Endpoints
- `GET /health` - Health status
- `GET /task/?focus_area=calibration` - Get single task
- `GET /task/batch?focus_area=calibration` - Get batch of tasks
- `POST /response/` - Submit model responses
- `GET /docs` - Interactive API reference

## 🧪 Testing
Run unit and integration tests:
```bash
pytest tests/
```

Run specific test:
```bash
pytest tests/unit/test_accuracy_scorer.py
```

## 📊 Data & Tasks
The project includes task banks for four focus areas:
- **Calibration** (`calib_tasks.jsonl`) - Model confidence accuracy
- **Error Detection** (`error_detect_tasks.jsonl`) - Identifying errors
- **Correction** (`correction_tasks.jsonl`) - Fixing mistakes
- **Certainty** (`certainty_tasks.jsonl`) - Confidence levels

Located in: `backend/task_registry/tasks/`

## 🛑 Stopping Services
Press **CTRL + C** in each terminal window

## 📖 Detailed Setup Guide
See **PROCEDURE.txt** for complete step-by-step instructions
"# MetaCog-BenchMark-Kaggle-Competition" 
