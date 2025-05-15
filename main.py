# main.py in the root directory
from fastapi import FastAPI
import importlib
from dotenv import load_dotenv
from  services.auth.auth_api import router as auth_router  # Import the router from auth_api.py
from services.agent.orchestrator.memory.chat_api import router as chat_router

load_dotenv()

# List of service modules (you can automate this discovery)
services = [
    "services.agent.grounding.upload.upload_api",
    "services.agent.grounding.vector_search_retrieval.vector_search_api",
    "services.agent.grounding.analyse_material.analyse_material_api",
    "services.agent.utils.summarize.summarize_api",
    "services.agent.utils.translate.translate_api",
    "services.agent.tools.plan_lesson.plan_lesson_api",
    "services.agent.tools.plan_course.plan_course_api",
    "services.agent.tools.generate_material.generate_material_api",
    "services.agent.tools.generate_activity.generate_activity_api",
    "services.agent.tools.evaluate.evaluate_api",
    "services.agent.tools.define_syllabus.define_syllabus_api",
]

# Create FastAPI app
app = FastAPI(
    title="EduPal APIs",
    description="APIs for E4E services",
    version="0.1.0",
    security=[{"bearerAuth": []}],
)

# Include the authentication router
app.include_router(chat_router)
app.include_router(auth_router)
print(f"Successfully loaded API routes from auth and chatbot modules")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint returning welcome message and API information."""
    return {
        "message": "Welcome to E4E API",
        "services": [service.split(".")[-1].replace("_api", "") for service in services],
        "docs_url": "/docs"
    }

# Register all service routers
for service_module in services:
    try:
        # Fix module names with hyphens for import
        import_path = service_module.replace("-", "_")
        module = importlib.import_module(import_path)
        
        # Look for the include_router function in each service module
        if hasattr(module, "include_router"):
            module.include_router(app)
            print(f"Successfully loaded API routes from {service_module}")
        else:
            print(f"Module {service_module} does not have include_router function")
    except ImportError as e:
        print(f"Could not import {service_module}: {e}")
