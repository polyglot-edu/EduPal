# main.py in the root directory
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import importlib
import asyncio
from contextlib import asynccontextmanager, suppress
from mcp_server import run_mcp_server
from dotenv import load_dotenv
from services.auth.auth_api import router as auth_router
from services.agent.orchestrator.chat.chat_api import router as chat_router
from services.database_management.OERs_api import router as OERs_router
from services.agent.grounding.vector_search_retrieval.vector_search_api import router as vector_search_router
from services.agent.grounding.analyse_material.analyse_material_api import router as analyse_material_router
import logging

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

# --------------------------
# LIFESPAN: safe startup/shutdown
# --------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Start background tasks (MCP server) and ensure clean shutdown.
    """
    tasks = []

    # Start MCP server task
    mcp_task = asyncio.create_task(run_mcp_server())
    tasks.append(mcp_task)

    try:
        yield  # FastAPI app is running
    finally:
        # Cancel all tasks
        for task in tasks:
            task.cancel()

        # Wait for graceful shutdown
        for task in tasks:
            with suppress(asyncio.CancelledError):
                try:
                    await asyncio.wait_for(task, timeout=3)
                except asyncio.TimeoutError:
                    logger.warning(f"Task {task.get_name()} did not shut down in time")

        logger.info("All background tasks stopped cleanly")

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
    return {
        "message": "Welcome to E4E API",
        "services": [service.split(".")[-1].replace("_api", "") for service in services],
        "docs_url": "/docs"
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
