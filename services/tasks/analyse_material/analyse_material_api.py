from fastapi import APIRouter, FastAPI, HTTPException, Header
from common.auth import authenticate
from .analyse_material_service import analysis
from .analyse_material_utils import AnalyseMaterialRequest, AnalyseMaterialResponse

router = APIRouter(
    prefix="/tasks",
    tags=["material"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/analyse_material", response_model=AnalyseMaterialResponse)
async def analyse_material( request: AnalyseMaterialRequest, access_key: str = Header(...) ):
    """
    Analyse a material and extract meaningful information. It's based on:

    - **text** _(str)_: The text to analyse.
    - **model** _(str)_: The model to use, default is "Gemini".

    Returns a JSON object with the following fields:

    - **language** _(str)_: The language of the material
    - **macro_subject** _(str)_: The macro subject of the material
    - **title** _(str)_: The title of the material
    - **education_level** _(str)_: The education level of the material
    - **learning_outcome** _(str)_: The learning outcome of the material
    - **topics** _(list[Topic])_: The topics of the material. Each topic is a list of:
        - **topic** _(str)_: The name of the topic
        - **explanation** _(str)_: The explanation of the topic
    - **keywords** _(list[str])_: The keywords of the material
    - **prerequisites** _(list[str])_: The prerequisites of the material
    - **estimated_duration** _(int)_: The estimated duration in minutes required to read and understand the generated material
    """

    try: 
        authenticate(access_key)

        if len(request.text) < 200:
            raise HTTPException(status_code=400, detail="Text must be at least 200 characters.")
        
        result = analysis(request)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
