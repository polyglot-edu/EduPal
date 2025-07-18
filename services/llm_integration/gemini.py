from google import genai
from google.genai import types

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
        response_model: Optional[Type[BaseModel]] = None,
        response_schema: Optional[str] = None, 
        context: Optional[str] = "",
        history: Optional[str] = "",
        options: Optional[Dict] = {"temperature": 0.0, "max_output_tokens": 1550},
        user_info: Optional[str] = "",
        instructions: Optional[str] = "",
        tools: Optional[List[str]] = None,
        image: Optional[Image.Image] = None,
    ) -> BaseModel | str:
        
        # compose the final prompt
        input_prompt = ""
        if instructions is not None and instructions != "":
            input_prompt += f"System Instructions: {instructions}\n"
        if context is not None and context != "":
            input_prompt += f"Context: {context}"
        if user_info is not None and user_info != "":
            input_prompt += f"\nUser Info: {user_info}"
        if history is not None and history != "":
            input_prompt += f"\nLatest Messages:\n{history}"
        input_prompt += f"\nrole:user\ncontent:{prompt}\nrole: assistant\ncontent:"
        # If tools are provided, add them to the input prompt
        if tools is not None and len(tools) > 0:
            input_prompt += f"\nTools: {', '.join(tools)}"
        # Describe the response shema if provided
        if response_schema is not None:
            input_prompt += f"\n\nOutput Response Schema: {response_schema}"

        #print(f"Input Prompt: {input_prompt}. \n")

        try:
            if image is not None:
                contents = [image, input_prompt]
            else:
                contents = input_prompt
            response = self.client.models.generate_content(
                model = self.model,
                contents = contents,
                config=genai.types.GenerateContentConfig(                   
                    response_mime_type='application/json' if response_model is not None else None,
                    response_schema=response_model if response_model is not None else None,
                    temperature=options.get('temperature', 0.1),
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
            if response_model is not None:
                # Parse the response into the specified Pydantic model
                return response.parsed
            # If no response model is specified, return the raw text
            return response.text
        except Exception as e:
            #print(f"Error generating JSON with Gemini: {e}")
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
            #print(f"Error generating image with Gemini: {e}")
            return ""
        