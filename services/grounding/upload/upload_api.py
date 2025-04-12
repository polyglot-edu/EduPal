from fastapi import APIRouter, FastAPI, HTTPException, Header
from pydantic import BaseModel
from .upload_service import upload_documents
from common.auth import authenticate
from dotenv import load_dotenv
import os

class UploadRequest(BaseModel):
    file: str
    uri: str = None
    db_name: str = None
    collection_name: str = None

class UploadResponse(BaseModel):
    results: str

router = APIRouter(
    prefix="/upload",
    tags=["grounding"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/upload", response_model=UploadResponse)
async def upload_file( request: UploadRequest, access_key: str = Header(...) ):
    """
    Upload a file (by path) and perform semantic chunking.

    - **file**: The path of the file to upload
    - **uri**: MongoDB connection URI
    - **db_name**: Database name
    - **collection_name**: Collection name
    """
    try: 
        authenticate(access_key)

        if not request.file.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")

        # Fallback to environment variables if empty
        if not request.uri or not request.db_name or not request.collection_name or request.uri == "" or request.db_name == "" or request.collection_name == "":
            print("Using environment variables for MongoDB connection details...")
            load_dotenv()
            request.uri = os.getenv("MONGO_URI", "")
            request.db_name = "edu_db"
            request.collection_name = "materials"

        # Ensure upload_documents is async, or remove await
        result = upload_documents(request.file, request.uri, request.db_name, request.collection_name)
        if result == 0:
            result = "Upload successful."
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return UploadResponse(results=result)

def include_router(app: FastAPI):
    app.include_router(router)
