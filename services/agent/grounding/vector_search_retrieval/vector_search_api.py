from fastapi import APIRouter, FastAPI, HTTPException, Header
import os

from services.agent.grounding.vector_search_retrieval.vector_search_utils import QueryRequest, QueryResponse, QueryResult
from .vector_search_service import query_OERs
from common.auth import authenticate

router = APIRouter(
    prefix="/vector-search",
    tags=["grounding"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/query", response_model=QueryResponse)
async def query_vector_search(request: QueryRequest, access_key: str = Header(...) ):
    """
    Query a collection about a specific topic.

    - **query**: The query to search for
    - **uri**: MongoDB connection URI
    - **db_name**: Database name
    - **collection_name**: Collection name

    Returns a List[Document] containing the search results

    """
    try:
        authenticate(access_key)
        
        if not request.query or len(request.query)<11:
            raise HTTPException(status_code=400, detail="Query is too short, please contextualize more.")
        
        # Fallback to environment variables if empty
        if not request.uri or not request.db_name or not request.collection_name or request.uri == "" or request.db_name == "" or request.collection_name == "":
            #print("Using environment variables for MongoDB connection details...")
            request.uri = os.getenv("MONGO_URI", "")
            request.db_name = "edu_db"
            request.collection_name = "materials"

        results = query_OERs(request.query, request.uri, request.db_name, request.collection_name)
        # Extract structured data: page number and content
        extracted_results = [
            QueryResult(
                page=int(doc.metadata.get("metadata", {}).get("page", -1)),  # Default to -1 if missing
                content=doc.page_content
            )
            for doc in results
        ]
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return QueryResponse(result = "Query successful.", search_results=extracted_results)

def include_router(app: FastAPI):
    app.include_router(router)
