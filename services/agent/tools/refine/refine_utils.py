from pydantic import BaseModel

from services.agent.utils.common_enums import print_enums

class RefineRequest(BaseModel):
    json_object: str
    instructions: str
    language: str = "English"
    model: str = "Gemini"

class Refinement(BaseModel):
    refined_json: str

def refine_prompt(request: RefineRequest) -> str:
    enums_info = print_enums() 
    prompt = f"""
You are an intelligent assistant. Your task is to refine a JSON object based on the user's instructions.

### Instructions
{request.instructions}

### Original JSON
{request.json_object}

### Notes:
- Keep the SAME JSON structure (do not add, remove, or rename any keys).
- Refine only the **values** of the JSON.
- If a value is an enum and you have to edit it, you can only change it to a valid value as listed below.
- Maintain the **original language** of the text values. The language is: **{request.language}**

### Enum Reference
{enums_info}

Return only the final, refined JSON string with the same structure.
"""

    return prompt



"""Test text:
{
  "json_object": "{\n  \"title\": \"Moto uniformemente accelerato\",\n  \"education_level\": \"elementary school\",\n  \"description\": \"Impara le basi della cinetica.\"\n}",
  "instructions": "Rendi la descrizione più coinvolgente e aggiungi dettagli sul tipo di piatti che verranno insegnati.",
  "language": "Italian",
  "model": "Gemini"
}
"""

