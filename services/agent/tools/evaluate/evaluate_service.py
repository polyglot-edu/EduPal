from services.llm_integration.llm_interface import get_llm
from .evaluate_utils import EvaluateRequest, EvaluateResponse, Evaluation, evaluate_prompt

def evaluation(request: EvaluateRequest):
    llm = get_llm(request.model)
    try:
        #print("Prompt: ",evaluate_prompt(request))
        #print("-"*100)
        #print("\n\n\n")
        response: EvaluateResponse = llm.generate_text(prompt=evaluate_prompt(request), response_model=EvaluateResponse)
        #print("Response",response)
        #print("-"*100)

        final = Evaluation(
            macro_subject=request.macro_subject,
            topic=request.topic,
            education_level=request.education_level,
            learning_outcome=request.learning_outcome,
            assignment=request.assignment,
            answer=request.answer,
            solutions=request.solutions,
            correctness_percentage=response.correctness_percentage,
            comment=response.comment,
            advice=response.advice,
            type=request.type,
            language=request.language,
        )

    except Exception as e:
        raise

    return final