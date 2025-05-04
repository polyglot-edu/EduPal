from fastapi import APIRouter, FastAPI, HTTPException, Header
from common.auth import authenticate
from .ground_service import ground
from .ground_utils import GroundRequest, GroundResponse

router = APIRouter(
    prefix="/tasks",
    tags=["material"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/ground", response_model=GroundResponse)
async def ground( request: GroundRequest, access_key: str = Header(...) ):
    """
    Grounds the context on a specific topic.

    - **query**: The query to search for
    - **uri**: MongoDB connection URI
    - **db_name**: Database name
    - **collection_name**: Collection name

    Returns a string containing the grounded context
    """

    try: 
        authenticate(access_key)

        if len(request.text) < 200:
            raise HTTPException(status_code=400, detail="Text must be at least 200 characters.")
        
        result = ground(request)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
