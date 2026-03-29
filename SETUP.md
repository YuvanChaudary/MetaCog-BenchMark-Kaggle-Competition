# Setup and Verification Instructions

## Section 8: Step-by-step local setup commands

```bash
# Clone and enter project
git clone https://github.com/your-org/metacognition-benchmark.git
cd metacognition-benchmark
# Expected: Directory changed to metacognition-benchmark
# Error: Repository not found -> Fix: Check git URL and access rights

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
# Expected: Prompt prefixed with (.venv)
# Error: python not found -> Fix: Ensure Python 3.11 is installed and in PATH

# Install all dependencies
pip install -r requirements.txt
# Expected: Successfully installed fastapi, duckdb, mlflow, etc.
# Error: PyTest/Pydantic version conflicts -> Fix: Delete existing .venv and start fresh

# Copy and configure .env
cp .env.example .env
# Expected: .env file created
# Error: cp command not found (Windows) -> Fix: copy .env.example .env

# Initialise DuckDB database
mkdir -p data
# Expected: data directory exists
# Error: mkdir not recognized (Windows) -> Fix: mkdir data

# Run database migrations (MVP: auto-schema via Python)
python -c "from backend.storage.results_db import ResultsDB; ResultsDB()"
# Expected: metacog.duckdb created in data/
# Error: ModuleNotFoundError -> Fix: Ensure .venv is activated

# Start MLflow tracking server
mlflow server --host 127.0.0.1 --port 5000
# Expected: Listening at: http://127.0.0.1:5000
# Error: port 5000 in use -> Fix: Kill process on port 5000

# Start FastAPI backend
uvicorn backend.api.main:app --reload
# Expected: Uvicorn running on http://127.0.0.1:8000
# Error: uvicorn not found -> Fix: Check virtual environment activation

# Start Streamlit dashboard
streamlit run streamlit_app/app.py
# Expected: Local URL: http://localhost:8501
# Error: No such file -> Fix: Ensure you are in project root

# Run full test suite
pytest tests/
# Expected: ============ X passed in Y.Zs ============
# Error: Module found but not imported -> Fix: set PYTHONPATH var

# Run only unit tests
pytest tests/unit/
# Expected: Unit tests pass
# Error: Folder tests/unit/ not found -> Fix: Verify you generated the folder structure

# Run only integration tests
pytest tests/integration/
# Expected: Integration tests pass
# Error: Folder tests/integration/ not found -> Fix: Verify structure

# Check test coverage
pytest tests/ --cov=backend
# Expected: Coverage summary printed
# Error: pytest-cov not installed -> Fix: pip install pytest-cov

# Run linter (ruff)
ruff check .
# Expected: No errors found.
# Error: ruff command not found -> Fix: pip install ruff

# Run type checker (mypy)
mypy backend
# Expected: Success: no issues found
# Error: mypy command not found -> Fix: pip install mypy
```

## Section 9: Frontend setup (React + Vite)

```bash
# Create Vite project
npm create vite@latest frontend -- --template react-ts
cd frontend

# Install dependencies
npm install recharts @types/recharts
npm install axios
npm install lucide-react
```

Update `vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

Update `tsconfig.json` compilerOptions:
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

## Section 10: Verification checklist

```markdown
[ ] GET http://localhost:8000/health returns {"status":"ok"}
    - Command: curl http://localhost:8000/health
    - Passing: {"status":"ok","version":"1.0.0"}
    - Error/Fix: Connection refused -> backend isn't running, start uvicorn

[ ] GET http://localhost:8000/task?focus_area=calibration returns a TaskObject
    - Command: curl "http://localhost:8000/task?focus_area=calib"
    - Passing: JSON response with task_id, focus_area, prompt, ground_truth
    - Error/Fix: 404 No tasks -> ensure TASK_BANK_PATH is correct and contains JSONL files

[ ] MLflow UI accessible at http://localhost:5000
    - Command: curl -s -o /dev/null -w "%{http_code}" http://localhost:5000
    - Passing: 200
    - Error/Fix: Connection refused -> mlflow server isn't running

[ ] Streamlit dashboard loads at http://localhost:8501
    - Command: curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/healthz
    - Passing: 200/404
    - Error/Fix: Connection refused -> start streamlit

[ ] pytest passes with 0 failures
    - Command: pytest tests/
    - Passing: All tests show green dots
    - Error/Fix: Tests failing -> Check code and env configs

[ ] DuckDB file exists at ./data/metacog.duckdb
    - Command: ls -l data/metacog.duckdb
    - Passing: File exists with file size > 0
    - Error/Fix: File not found -> Execute the DB init script

[ ] .env is NOT committed to git (check .gitignore works)
    - Command: git status
    - Passing: .env is ignored and doesn't show in untracked files
    - Error/Fix: Shows as untracked -> Ensure .env is in .gitignore

[ ] docker-compose up --build completes with no errors
    - Command: docker-compose up --build -d
    - Passing: Creating backend ... done, Creating streamlit ... done
    - Error/Fix: Port already in use -> Stop local uvicorn/streamlit processes
```
