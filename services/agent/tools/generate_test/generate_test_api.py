import json
from typing import Optional
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Header, UploadFile
from common.auth import authenticate
from .generate_test_service import create_test
from .generate_test_utils import GenerateTestRequest
from ..generate_activity.generate_activity_utils import Activity

router = APIRouter(
    prefix="/tasks",
    tags=["activity"],
    responses={ 400: {"description": "Bad Request"},
                401: {"description": "Unauthorized"},
                404: {"description": "Not found"},
                500: {"description": "Internal Server Error"}},
)

@router.post("/generate_test", response_model=list[Activity])
async def generate_complete_test(access_key: str = Header(...), data: str = Form(...), material: Optional[UploadFile] = File(None) ):
    """
Generate a complete test for a given set of topics based on:

- **macro_subject** _(str)_: the macro subject of the topic
- **topic** _(str)_: the topic of the activity
- **education_level** _(EducationLevel)_: the education level of the activity
- **topics** _(list[TopicParams])_: the list of topics to generate the test for, each topic has:
    - **topic_name** _(str)_: the name of the topic
    - **topic_explanation** _(str)_: the explanation of the topic
    - **learning_outcome** _(LearningOutcome)_: the learning outcome of the topic
    - **exercise_params** _(list[ActivityParams])_: the list of exercise parameters for the topic, each parameter has:
        - **type** _(TypeOfActivity)_: the type of the activity
        - **solutions_number** _(int)_: the number of solutions to generate
        - **distractors_number** _(int)_: the number of distractors to generate. The distractors are answers similar to the correct answer, that are used to confuse the audience
        - **easily_discardable_distractors_number** _(int)_: the number of distractors to generate. The distractors are completely wrong answers, that are easy to discard
- **material** _(Union[UploadFile, list[Resource]])_: the material to use for generating the test, can be a file or a list of resources
- **learning_outcome** _(LearningOutcome)_: the learning outcome of the test
- **exercises** _(list[ActivityParams])_: the list of exercise parameters for the test, each parameter has:
    - **type** _(TypeOfActivity)_: the type of the activity
    - **solutions_number** _(int)_: the number of solutions to generate
    - **distractors_number** _(int)_: the number of distractors to generate. The distractors are answers similar to the correct answer, that are used to confuse the audience
    - **easily_discardable_distractors_number** _(int)_: the number of distractors to generate. The distractors are completely wrong answers, that are easy to discard
- **language** _(str)_: the language of the activity, defaults to English
- **model** _(str)_: the model to use, defaults to Gemini

Returns a list of JSON objects with the following fields:

- **macro_subject** _(str)_: the macro subject of the topic
- **topic** _(str)_: the topic of the activity
- **education_level** _(EducationLevel)_: the education level of the activity
- **learning_outcome** _(LearningOutcome)_: the learning outcome of the activity
- **material** _(str)_: the material to use for generating the activity
- **params** _(list[ActivityParams])_: the parameters for the activity        
- generated_activities _(list[GeneratedActivity])_: the generated activities based on the provided parameters:
    - **type** _(TypeOfActivity)_: the type of the activity
    - **assignment** _(str)_: the assignment of the activity- **assignment** _(str)_: the assignment of the activity
    - **plus** _(str)_: the plus of the activity
    - **solutions** _(list[str])_: the solutions of the activity
    - **distractors** _(list[str])_: the distractors of the activity
    - **easily_discardable_distractors** _(list[str])_: the easily_discardable_distractors of the activity
- **language** _(str)_: the language of the activity, defaults to English
- **model** _(str)_: the model to use, defaults to Gemini

### 🔧 How the API Works

1. **Input Validation**  
   - If neither **topics** nor **material** are provided, an error is raised.  
   - If a **material file** is provided, it is analyzed to extract topics.

---

### 📌 Step 1 – Obtain Final Topics

#### A. If a list of exercise types is provided:
- If **topics are already present**:  
  - Decide which topic to associate with each exercise.  
  - If some topics already have exercises assigned, remove those exercises from the original exercise list.
  
- If **no topics are provided**, but **material exists**:  
  - Extract topics from the material.

- Then:  
  - Randomly associate remaining exercises with topics.  
  - Remove all topics that ended up with no associated exercises.

#### B. If **no exercise types are specified**:
- If **topics are not present** but **material is**, extract topics from the material.  
- If **topics are already provided**, do nothing.

- Then:  
  - Generate one random exercise type for each topic.

---

### 🧠 Step 2 – Generate Exercises for Each Topic

#### A. If material is provided:
- Perform **vector search** to retrieve the most relevant snippets for each topic.

#### B. If no material is provided:
- Instruct the **LLM** to use its own internal knowledge.

---

### 📤 Final Step

- Map all collected information into the request format expected by the activity generation engine.  
- Call the **LLM** to generate the exercises.  
- Return a single list containing all generated activities.

    """

    try: 
        request: GenerateTestRequest = GenerateTestRequest(**json.loads(data))
        if material:
            request.material = material
        authenticate(access_key)
        result = await create_test(request)

    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        else:
            raise RuntimeError(f"Unexpected error: {e}")

    return result

def include_router(app: FastAPI):
    
    app.include_router(router)

