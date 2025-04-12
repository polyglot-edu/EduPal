from fastapi import APIRouter, FastAPI, HTTPException, Header
from common.auth import authenticate
from .plan_lesson_service import lesson_plan
from .plan_lesson_utils import PlanLessonRequest, LessonPlan

router = APIRouter(
    prefix="/tasks",
    tags=["plan"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/plan_lesson", response_model=LessonPlan)
async def plan_lesson( request: PlanLessonRequest, access_key: str = Header(...) ):
    """
    Plan a lesson based on:\n

    - **topics** _(list[Topic])_: a list of topics to be covered in the lesson. Each topic should be a dictionary with the following keys:
        - **topic** _(str)_: the topic to be covered
        - **explanation** _(str)_: a brief explanation of the topic
        - **learning_outcome** _(LearningOutcome)_: the desired learning outcome for the specific topic
    - **learning_outcome** _(LearningOutcome)_: the desired learning outcome for the lesson
    - **language** _(str)_: the language of the lesson, defaults to "English"
    - **macro_subject** _(str)_: the macro subject of the lesson (for example, "Mathematics", "Science", etc.)
    - **title** _(str)_: the title of the lesson
    - **education_level** _(EducationLevel)_: the education level of the audience
    - **context** _(str)_: the audience context, it is used to tailor the suggestions for the learning activity to the specific audience
    - **model** _(str)_: the model to be used for the lesson, defaults to Gemini

    Returns a JSON object containing the lesson plan, including:

    - **title** _(str)_: the title of the lesson
    - **macro_subject** _(str)_: the macro subject of the lesson
    - **education_level** _(EducationLevel)_: the education level of the audience
    - **learning_outcome** _(LearningOutcome)_: the desired learning outcome for the lesson
    - **prerequisites** _(list[str])_: a list of prerequisites for the lesson
    - **nodes** _(list[Node])_: a list of nodes for the lesson, where each node is a dictionary with the following keys:
        - **type** _(TypeOfActivity)_: the type of activity (for example, "lecture", "discussion", etc.)
        - **topic** _(str)_: the topic of the activity
        - **details** _(str)_: the details of the activity
        - **learning_outcome** _(LearningOutcome)_: the desired learning outcome for the activity
        - **duration** _(int)_: the duration of the activity in minutes
    **context** _(str)_: the audience context
    **language** _(str)_: the language of the lesson
    """
    try: 
        authenticate(access_key)
        result = lesson_plan(request)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
