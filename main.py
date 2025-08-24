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
# LIFESPAN: minimal startup/shutdown
# --------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events."""
    # Start MCP server in a background thread
    def start_mcp():
        asyncio.run(run_mcp_server())

    thread = threading.Thread(target=start_mcp, daemon=True)
    thread.start()
    
    yield  # This marks the point where the app is ready to handle requests

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

