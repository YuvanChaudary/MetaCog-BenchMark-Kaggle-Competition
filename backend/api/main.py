import time
import json
import logging
import asyncio
from uuid import uuid4
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

# Relative application imports
from backend.core.config import settings
from backend.core.logging_config import setup_logging
from backend.api.task_dispatcher import router as task_router
from backend.api.response_collector import router as response_router
from backend.api.health import router as health_router

from backend.storage.results_db import ResultsDB
from backend.task_registry.task_loader import TaskLoader, TaskBankExhaustedError
from backend.evaluation.calibration_engine import CalibrationEngine

logger = logging.getLogger(__name__)

# Predefined benchmark focus areas
FOCUS_AREAS = ["calibration", "error_detection", "correction", "certainty"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    setup_logging()
    
    # 3. Initialise and open ResultsDB
    db = ResultsDB(
        backend=settings.DATABASE_BACKEND,
        connection_string=settings.DATABASE_CONNECTION_POOL
    )
    db.initialise()
    app.state.db = db
    
    # 4. Initialise TaskLoader for each focus area
    app.state.task_loaders = {}
    for focus in FOCUS_AREAS:
        app.state.task_loaders[focus] = TaskLoader(
            task_bank_path=settings.FILE_PATH_TASK_BANK,
            include_contested=settings.EVALUATION_INCLUDE_CONTESTED
        )
        
    # 5. Initialise one CalibrationEngine per focus area
    app.state.calib_engines = {}
    for focus in FOCUS_AREAS:
        app.state.calib_engines[focus] = CalibrationEngine()
        
    # 6. Initialise empty set for websockets
    app.state.ws_connections = set()
    
    # 7. Log Ok Output
    logger.info(json.dumps({
        "event": "startup",
        "status": "ok",
        "database": settings.DATABASE_BACKEND
    }))
    
    yield
    
    # SHUTDOWN
    if hasattr(app.state, "db") and app.state.db:
        app.state.db.close()
        
    logger.info(json.dumps({
        "event": "shutdown",
        "reason": "normal"
    }))


def create_app() -> FastAPI:
    """Application factory for injection readiness."""
    app = FastAPI(lifespan=lifespan)
    
    # MIDDLEWARE (1. CORSMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # MIDDLEWARE (2. Request Timing, 3. Request ID Injection)
    @app.middleware("http")
    async def global_middleware(request: Request, call_next):
        req_id = str(uuid4())
        # Attach request ID internally across the application loop
        request.state.request_id = req_id
        
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            # Middleware interception logic to inject diagnostic headers prior to response exit
            elapsed = time.perf_counter() - start_time
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Process-Time"] = f"{elapsed:.4f}s"
            return response
        except Exception as e:
            # We strictly catch and forward exceptions rather than silently swallowing inside the loop
            raise e

    # ROUTERS
    app.include_router(health_router)
    app.include_router(task_router, prefix="/task")
    app.include_router(response_router, prefix="/response")
    
    # WEBSOCKET ENDPOINT: /ws/feed
    @app.websocket("/ws/feed")
    async def ws_feed(websocket: WebSocket):
        await websocket.accept()
        app.state.ws_connections.add(websocket)
        try:
            while True:
                await websocket.send_json({"type": "ping"})
                await asyncio.sleep(30)
        except WebSocketDisconnect:
            app.state.ws_connections.discard(websocket)

    # GLOBAL EXCEPTION HANDLERS
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "request_id": req_id}
        )

    @app.exception_handler(TaskBankExhaustedError)
    async def task_exhausted_handler(request: Request, exc: TaskBankExhaustedError):
        return JSONResponse(
            status_code=404,
            content={
                "detail": "task_bank_exhausted",
                "message": "All tasks have been served for this configuration."
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        req_id = getattr(request.state, "request_id", "unknown")
        logger.error(f"Internal Error | Request ID: {req_id}", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "internal_error", "request_id": req_id}
        )

    return app


# BROADCAST HELPER (module-level coroutine)
async def broadcast_result(app: FastAPI, result: dict) -> None:
    dead = set()
    for ws in app.state.ws_connections:
        try:
            await ws.send_json(result)
        except Exception:
            dead.add(ws)
    # Perform subtraction assignment operation safely resolving dead nodes silently
    app.state.ws_connections -= dead


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None
    )
