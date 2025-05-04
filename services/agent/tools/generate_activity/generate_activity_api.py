from fastapi import APIRouter, FastAPI, HTTPException, Header
from common.auth import authenticate
from .generate_activity_service import activity
from .generate_activity_utils import GenerateActivityRequest, Activity

router = APIRouter(
    prefix="/tasks",
    tags=["activity"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/generate_activity", response_model=Activity)
async def generate_activity( request: GenerateActivityRequest, access_key: str = Header(...) ):
    """
    Generate activity for a given topic based on:

    - **macro_subject** _(str)_: the macro subject of the topic
    - **topic** _(str)_: the topic of the activity
    - **education_level** _(EducationLevel)_: the education level of the activity
    - **learning_outcome** _(LearningOutcome)_: the learning outcome of the activity
    - **material** _(str)_: the material to use for generating the activity
    - **solutions_number** _(int)_: the number of solutions to generate
    - **distractors_number** _(int)_: the number of distractors to generate. The distractors are answers similar to the correct answer, that are used to confuse the audience
    - **easily_discardable_distractors_number** _(int)_: the number of distractors to generate. The distractors are completely wrong answers, that are easy to discard
    - **type** _(TypeOfActivity)_: the type of the activity
    - **language** _(str)_: the language of the activity, defaults to English
    - **model** _(str)_: the model to use, defaults to Gemini

    Returns a JSON object with the following fields:

    - **macro_subject** _(str)_: the macro subject of the topic
    - **topic** _(str)_: the topic of the activity
    - **education_level** _(EducationLevel)_: the education level of the activity
    - **learning_outcome** _(LearningOutcome)_: the learning outcome of the activity
    - **material** _(str)_: the material to use for generating the activity
    - **assignment** _(str)_: the assignment of the activity
    - **plus** _(str)_: the plus of the activity
    - **solutions** _(list[str])_: the solutions of the activity
    - **distractors** _(list[str])_: the distractors of the activity
    - **easily_discardable_distractors** _(list[str])_: the easily_discardable_distractors of the activity
    - **type** _(TypeOfActivity)_: the type of the activity
    - **language** _(str)_: the language of the activity, defaults to English
    """

    try: 
        authenticate(access_key)
        result = activity(request)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
