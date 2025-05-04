from fastapi import APIRouter, FastAPI, HTTPException, Header
from common.auth import authenticate
from .generate_material_service import material
from .generate_material_utils import GenerateMaterialRequest, Material

router = APIRouter(
    prefix="/tasks",
    tags=["material"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/generate_material", response_model=Material)
async def generate_material( request: GenerateMaterialRequest, access_key: str = Header(...) ):
    """
    Generate material for a given topic based on:

    - **title** _(str)_: the title of the topic
    - **macro_subject** _(str)_: the macro subject of the topic
    - **topics** _(list[LessonNode])_: the topics to cover. Each topic is a list of:
        - **title** _(str)_: the title of the topic
        - **learning_outcome** _(LearningOutcome)_: the learning outcome of the topic
        - **topics** _(list[Topic])_: the topics to cover. Each topic is a list of:
            - **topic** _(str)_: the topic
            - **explanation** _(str)_: the explanation of the topic
    - **education_level** _(EducationLevel)_: the education level of the audience
    - **learning_outcome** _(LearningOutcome)_: the learning outcome of the material
    - **duration** _(int)_: the duration of the material
    - **language** _(str)_: the language of the material, defaults to English
    - **model** _(str)_: the model to use, defaults to Gemini

    Returns a JSON object with the following fields:

    - **title** _(str)_: the title of the topic
    - **macro_subject** _(str)_: the macro subject of the topic
    - **topics** _(list[LessonNode])_: the topics to cover. Each topic is a list of:
        - **title** _(str)_: the title of the topic
        - **learning_outcome** _(LearningOutcome)_: the learning outcome of the topic
        - **topics** _(list[Topic])_: the topics to cover. Each topic is a list of:
            - **topic** _(str)_: the topic
            - **explanation** _(str)_: the explanation of the topic
    - **education_level** _(EducationLevel)_: the education level of the audience
    - **learning_outcome** _(LearningOutcome)_: the learning outcome of the material
    - **duration** _(int)_: the duration of the material
    - **material** _(str)_: the generated material
    - **language** _(str)_: the language of the material, defaults to English
    """

    try: 
        authenticate(access_key)
        result = material(request)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
