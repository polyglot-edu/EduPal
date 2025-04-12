from google import genai
from typing import Optional, List, Dict, Type
from pydantic import BaseModel
from PIL import Image
from .llm_interface import LLMInterface
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")

class GeminiLLM(LLMInterface):
    def __init__(self):
        self.client = genai.Client(api_key=API_KEY)
        self.model = "gemini-2.0-flash"
        self.image_model = "gemini-2.0-flash"

    def generate_text(
        self,
        prompt: str,
        context: Optional[List[str]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        options: Optional[Dict] = {"temperature": 0.0, "max_output_tokens": 1550},
        user_info: Optional[Dict] = None,
        instructions: Optional[str] = "",
    ) -> str:
        
        # compose the final prompt
        input_prompt = ""
        if context is not None:
            input_prompt += "\n\nContext:\n" + "\n".join(context)
        if history is not None:
            for turn in history:
                input_prompt += f"\nUser: {turn['user']}\nAssistant: {turn['assistant']}"
        if user_info is not None:
            input_prompt += f"\nLong Term Memory User Info: {user_info}"
        input_prompt += f"\n\n{prompt}"

        try:
            response = self.client.models.generate_content(
                model = self.model,
                contents = input_prompt,
                config = genai.types.GenerateContentConfig(
                    system_instruction=instructions,
                    temperature=options.get('temperature', 0.0),
                    #top_p=0.95,
                    #top_k=20,
                    #candidate_count=1,
                    #seed=5,
                    #max_output_tokens=100,
                    #stop_sequences=['STOP!'],
                    #presence_penalty=0.0,
                    #frequency_penalty=0.0,
                    ),
            )
            return response.text
        except Exception as e:
            print(f"Error generating text with Gemini: {e}")
            return ""

    def generate_json(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        context: Optional[List[str]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        options: Optional[Dict] = {"temperature": 0.0, "max_output_tokens": 1550},
        user_info: Optional[Dict] = None,
        instructions: Optional[str] = "",
    ) -> BaseModel:
        
        # compose the final prompt
        input_prompt = ""
        if context is not None:
            input_prompt += "\n\nContext:\n" + "\n".join(context)
        if history is not None:
            for turn in history:
                input_prompt += f"\nUser: {turn['user']}\nAssistant: {turn['assistant']}"
        if user_info is not None:
            input_prompt += f"\nLong Term Memory User Info: {user_info}"
        input_prompt += f"\n\n{prompt}"

        try:
            response = self.client.models.generate_content(
                model = self.model,
                contents = input_prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=response_model,
                    system_instruction=instructions,
                    temperature=options.get('temperature', 0.0),
                    #top_p=0.95,
                    #top_k=20,
                    #candidate_count=1,
                    #seed=5,
                    #max_output_tokens=100,
                    #stop_sequences=['STOP!'],
                    #presence_penalty=0.0,
                    #frequency_penalty=0.0,
                    ),
            )
            return response.parsed
        except Exception as e:
            print(f"Error generating JSON with Gemini: {e}")
            return ""
        
    def generate_image(
        self,
        prompt: str,
    ) -> Image:
        try:
            # Generate Image
            response = self.client.models.generate_images(
                model= self.image_model,
                prompt=prompt,
                config=genai.types.GenerateImagesConfig(
                    number_of_images=1,
                    include_rai_reason=True,
                    output_mime_type='image/jpeg',
                ),
            )
            return response.generated_images[0].image
        except Exception as e:
            print(f"Error generating image with Gemini: {e}")
            return ""
        