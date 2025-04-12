from fastapi import APIRouter, FastAPI, HTTPException, Header
from common.auth import authenticate
from .evaluate_service import evaluation
from .evaluate_utils import EvaluateRequest, Evaluation

router = APIRouter(
    prefix="/tasks",
    tags=["activity"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/evaluate", response_model=Evaluation)
async def evaluate( request: EvaluateRequest, access_key: str = Header(...) ):
    """
    Evaluate an activity based on:

    - **macro_subject** _(str)_: the macro subject of the topic
    - **topic** _(str)_: the topic of the activity
    - **education_level** _(EducationLevel)_: the education level of the audience
    - **learning_outcome** _(LearningOutcome)_: the learning outcome of the activity
    - **assignment** _(str)_: the assignment of the activity
    - **answer** _(str)_: the answer of the activity
    - **solutions** _(list[str])_: a list of the solutions of the activity
    - **type** _(TypeOfActivity)_: the type of the activity
    - **language** _(str)_: the language of the activity, defaults to English
    - **model** _(str)_: the model to use, defaults to Gemini

    Returns a JSON object with the following fields:

    - **macro_subject** _(str)_: the macro subject of the topic
    - **topic** _(str)_: the topic of the activity
    - **education_level** _(EducationLevel)_: the education level of the audience
    - **learning_outcome** _(LearningOutcome)_: the learning outcome of the activity
    - **assignment** _(str)_: the assignment of the activity
    - **answer** _(str)_: the answer of the activity
    - **solutions** _(list[str])_: a list of the solutions of the activity
    - **correctness_percentage** _(int)_: a numerical result of the activity
    - **comment** _(str)_: a comment on the activity
    - **advice** _(str)_: a pedagogical advice on the activity
    - **type** _(TypeOfActivity)_: the type of the activity
    - **language** _(str)_: the language of the activity, defaults to English
    """

    try: 
        authenticate(access_key)
        result = evaluation(request)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
