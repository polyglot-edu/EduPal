from services.llm_integration.llm_interface import get_llm
from .plan_course_utils import PlanCourseRequest, PlanCourseResponse, CoursePlan, plan_course_prompt

def course_plan(request: PlanCourseRequest):
    llm = get_llm(request.model)
    try:
        response: PlanCourseResponse = llm.generate_text(prompt=plan_course_prompt(request), response_model=PlanCourseResponse)
        #print("Response",response)
        #print("-"*50)

        final = CoursePlan(
            title=request.title,
            macro_subject=request.macro_subject,
            education_level=request.education_level,
            learning_objectives=request.learning_objectives,
            number_of_lessons=request.number_of_lessons,
            duration_of_lesson=request.duration_of_lesson,
            prerequisites=response.prerequisites,
            nodes=response.nodes,
            language=request.language
        )
   
    except Exception as e:
        raise

    return final
