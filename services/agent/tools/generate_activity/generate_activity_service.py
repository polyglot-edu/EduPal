from services.llm_integration.llm_interface import get_llm
from .generate_activity_utils import GenerateActivityRequest, Activity, GeneratedActivity, generate_activity_prompt

def activity(request: GenerateActivityRequest):
    llm = get_llm(request.model)
    try:
        #print("Prompt: ",generate_activity_prompt(request))
        #print("-"*100)
        #print("\n\n\n")
        response: list[GeneratedActivity] = llm.generate_text(prompt=generate_activity_prompt(request), response_model=list[GeneratedActivity])
        #print("Response",response)
        #print("-"*100)

        final = Activity(
            macro_subject=request.macro_subject,
            topic=request.topic,
            topic_explanation=request.topic_explanation,
            education_level=request.education_level,
            learning_outcome=request.learning_outcome,
            material=request.material,
            params=request.params,
            generated_activities=response,
            language=request.language,
            model=request.model
        )
            
    except Exception as e:
        raise

    return final