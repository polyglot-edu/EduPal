from services.llm_integration.llm_interface import get_llm
from .refine_utils import RefineRequest, Refinement, refine_prompt

def refinement(request: RefineRequest):
    llm = get_llm(request.model)
    try:
        #print("Prompt: ",refine_prompt(request))
        #print("-"*100)
        #print("\n\n\n")
        response: Refinement = llm.generate_text(prompt=refine_prompt(request), response_model=Refinement)
        #print("Response",response)
        #print("-"*100)

        final = Refinement(
            refined_json=response.refined_json
        )

    except Exception as e:
        raise

    return final