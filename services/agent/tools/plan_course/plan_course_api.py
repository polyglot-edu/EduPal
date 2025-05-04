from fastapi import APIRouter, FastAPI, HTTPException, Header
from common.auth import authenticate
from .plan_course_service import course_plan
from .plan_course_utils import PlanCourseRequest, CoursePlan

router = APIRouter(
    prefix="/tasks",
    tags=["plan"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/plan_course", response_model=CoursePlan)
async def plan_course( request: PlanCourseRequest, access_key: str = Header(...) ):
    """
    Plan a course based on:

    - **title** _(str)_: the title of the lesson
    - **macro_subject** _(str)_: the macro subject of the lesson
    - **education_level** _(EducationLevel)_: the education level of the lesson
    - **learning_objectives** _(LearningObjectives)_: the learning objectives of the lesson:
        - **knowledge** _(str)_: the knowledge the learner should acquire during the course
        - **skills** _(str)_: The skills that the learner should have at the end of the course.
        - **attitude** _(str)_: The attitude that the learner should develop during the course.
    - **number_of_lessons** _(int)_: the number of lessons in the course
    - **duration_of_lesson** _(int)_: the duration (in minutes) of each lesson
    - **language** _(str)_: the language of the course
    - **model** _(str)_: the model to be used for the course, defualts to Gemini

    Returns a JSON object with the following fields:

    - **title** _(str)_: the title of the lesson
    - **macro_subject** _(str)_: the macro subject of the lesson
    - **education_level** _(EducationLevel)_: the education level of the lesson
    - **learning_objectives** _(LearningObjectives)_: the learning objectives of the lesson:
    - **number_of_lessons** _(int)_: the number of lessons in the course
    - **duration_of_lesson** _(int)_: the duration (in minutes) of each lesson
    - **prerequisites** _(list[str])_: the prerequisites for the course
    - **nodes** _(list[LessonNode])_: the nodes of the course:
        - **title** _(str)_: the title of the lesson
        - **learning_outcome** _(LearningOutcome)_: the macro subject of the lesson
        - **topics** _(list[Topic])_: the topics of the lesson:
            - **topic** _(str)_: the topic of the lesson
            - **explanation** _(str)_: the explanation of the topic
    - **language** _(str)_: the language of the course, defaults to English
    """

    try: 
        authenticate(access_key)
        result = course_plan(request)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    app.include_router(router)
