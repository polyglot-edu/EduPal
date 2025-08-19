# main.py in the root directory
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import importlib
import asyncio
import threading
from contextlib import asynccontextmanager
from mcp_server import run_mcp_server
from dotenv import load_dotenv
from services.auth.auth_api import router as auth_router
from services.agent.orchestrator.chat.chat_api import router as chat_router
from services.database_management.OERs_api import router as OERs_router
from services.agent.grounding.vector_search_retrieval.vector_search_api import router as vector_search_router
from services.agent.grounding.analyse_material.analyse_material_api import router as analyse_material_router
import logging
import atexit
import os

logger = logging.getLogger(__name__)
load_dotenv()

# List of service modules
services = [
    "services.agent.utils.summarize.summarize_api",
    "services.agent.utils.translate.translate_api",
    "services.agent.tools.plan_lesson.plan_lesson_api",
    "services.agent.tools.plan_course.plan_course_api",
    "services.agent.tools.generate_material.generate_material_api",
    "services.agent.tools.generate_activity.generate_activity_api",
    "services.agent.tools.evaluate.evaluate_api",
    "services.agent.tools.define_syllabus.define_syllabus_api",
    "services.agent.tools.refine.refine_api",
    "services.agent.tools.generate_test.generate_test_api",
]

# Global MCP server management
_mcp_thread = None
_mcp_loop = None
_mcp_task = None

def run_mcp_in_thread():
    """Run MCP server in its own event loop in a separate thread"""
    global _mcp_loop, _mcp_task
    
    # Create a new event loop for this thread
    _mcp_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_mcp_loop)
    
    try:
        # Start the MCP server
        _mcp_task = _mcp_loop.create_task(run_mcp_server())
        logger.info("MCP server started in separate thread")
        
        # Run the event loop
        _mcp_loop.run_until_complete(_mcp_task)
    except Exception as e:
        logger.error(f"MCP server error: {e}")
    finally:
        logger.info("MCP server thread ending")

def start_persistent_mcp_server():
    """Start MCP server in a separate thread that persists across reloads"""
    global _mcp_thread
    
    # Check if MCP server is already running
    if _mcp_thread and _mcp_thread.is_alive():
        logger.info("MCP server already running")
        return
    
    # Start MCP server in a daemon thread
    _mcp_thread = threading.Thread(target=run_mcp_in_thread, daemon=True)
    _mcp_thread.start()
    logger.info("MCP server thread started")

def stop_mcp_server():
    """Stop the MCP server gracefully"""
    global _mcp_loop, _mcp_task, _mcp_thread
    
    if _mcp_task and _mcp_loop and not _mcp_task.done():
        try:
            # Schedule cancellation in the MCP loop
            _mcp_loop.call_soon_threadsafe(_mcp_task.cancel)
            logger.info("MCP server cancellation requested")
        except Exception as e:
            logger.error(f"Error cancelling MCP server: {e}")

# Register cleanup function for process exit
atexit.register(stop_mcp_server)

# Start MCP server when module is imported
# This happens once when uvicorn loads the module, not on every reload
if not _mcp_thread or not _mcp_thread.is_alive():
    start_persistent_mcp_server()

# --------------------------
# LIFESPAN: minimal startup/shutdown
# --------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Minimal lifespan - MCP server runs independently
    """
    logger.info("FastAPI starting up")
    
    # Ensure MCP server is running
    if not _mcp_thread or not _mcp_thread.is_alive():
        start_persistent_mcp_server()
    
    try:
        yield  # FastAPI app is running
    finally:
        logger.info("FastAPI shutting down")
        # Don't stop MCP server on reload, only on process exit

# --------------------------
# FASTAPI APP
# --------------------------
app = FastAPI(
    title="EduPal APIs",
    description="APIs for E4E services",
    version="0.1.0",
    security=[{"bearerAuth": []}],
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
for router in [chat_router, auth_router, OERs_router, vector_search_router, analyse_material_router]:
    app.include_router(router)

# Root endpoint
@app.get("/")
async def root():
    mcp_status = "running" if _mcp_thread and _mcp_thread.is_alive() else "stopped"
    return {
        "message": "Welcome to E4E API",
        "mcp_server_status": mcp_status,
        "services": [service.split(".")[-1].replace("_api", "") for service in services],
        "docs_url": "/docs"
    }

# Health check endpoint
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mcp_server_running": _mcp_thread and _mcp_thread.is_alive()
    }

# Dynamically register service routers
for service_module in services:
    try:
        import_path = service_module.replace("-", "_")
        module = importlib.import_module(import_path)
        if hasattr(module, "include_router"):
            module.include_router(app)
        else:
            logger.error(f"Module {service_module} has no include_router function")
    except ImportError as e:
        logger.error(f"Could not import {service_module}: {e}")

# --------------------------
# RUN Uvicorn (with reload)
# --------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["services"],  # watch your nested directories
        log_level="info"
    )