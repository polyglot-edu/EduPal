from fastapi import APIRouter, FastAPI, HTTPException, Header
from common.auth import authenticate
from common.tier_restrictions import enforce_own_key_required
from .refine_service import refinement
from .refine_utils import RefineRequest, Refinement

router = APIRouter(
    prefix="/tasks",
    tags=["general"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/refine", response_model=Refinement)
async def refine( request: RefineRequest, access_key: str = Header(...), llm_token: str | None = Header(None, alias="llm_token") ):
    """
    Refine an object based on:

    - **json** _(str)_: the json of the object to be refined
    - **instructions** _(str)_: the instructions to refine the object
    - **language** _(str)_: the language of the object, defaults to English
    - **model** _(str)_: the model to use, defaults to Gemini

    Returns a string object with the same format of the json input:

    - **refined_json** _(str)_: the refined JSON object
    """

    try:
        authenticate(access_key)
        enforce_own_key_required(llm_token, "Refinement")
        result = refinement(request, llm_token=llm_token)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
