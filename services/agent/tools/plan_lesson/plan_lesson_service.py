from services.llm_integration.llm_interface import get_llm
from .plan_lesson_utils import PlanLessonRequest, PlanLessonResponse, LessonPlan, plan_lesson_prompt

def lesson_plan(request: PlanLessonRequest, llm_token: str | None = None):
    llm = get_llm(request.model, api_key=llm_token)
    try:
        response: PlanLessonResponse = llm.generate_text(prompt=plan_lesson_prompt(request), response_model=PlanLessonResponse)
        
        final = LessonPlan(
            title=request.title,
            macro_subject=request.macro_subject,
            education_level=request.education_level,
            learning_outcome=request.learning_outcome,
            prerequisites=response.prerequisites,
            nodes=response.nodes,
            context=request.context,
            language=request.language
        )

    except Exception as e:
        raise

    return final
