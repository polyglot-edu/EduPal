from io import BytesIO
import json
from pydantic import RootModel
from openai import AzureOpenAI
from typing import Optional, List, Dict, Type, get_origin, get_args
from pydantic import BaseModel
from PIL import Image
import os, requests
from .llm_interface import LLMInterface
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = "2024-12-01-preview"
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("OPENAI_DEPLOYMENT_NAME")
IMAGE_GEN_MODEL = os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "dall-e-3")


class AzureOpenAILLM(LLMInterface):
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION
        )
        self.deployment = AZURE_OPENAI_DEPLOYMENT_NAME

    def generate_text(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        context: Optional[str] = "",
        history: Optional[str] = "",
        options: Optional[Dict] = {"temperature": 0.0, "max_tokens": 1000},
        user_info: Optional[str] = "",
        instructions: Optional[str] = "",
        tools: Optional[List[str]] = None,
        image: Optional[Image.Image] = None,  # Not supported
    ) -> BaseModel | List[BaseModel] | str:

        # Handle list[BaseModel] response
        wrapper_model = None
        is_list_response = False
        if response_model and get_origin(response_model) is list:
            is_list_response = True
            item_model = get_args(response_model)[0]

            class WrapperModel(RootModel[List[item_model]]):
                @classmethod
                def model_validate(cls, obj):
                    # If obj is dict with root key, unwrap it
                    if isinstance(obj, dict) and "root" in obj:
                        obj = obj["root"]
                    # If obj is list of dicts with root key, unwrap each item
                    if isinstance(obj, list):
                        new_list = []
                        for item in obj:
                            if isinstance(item, dict) and "root" in item:
                                new_list.append(item["root"])
                            else:
                                new_list.append(item)
                        obj = new_list
                    # Now call super to validate as list of item_model
                    return super().model_validate(obj)

            wrapper_model = WrapperModel
        else:
            wrapper_model = response_model

        # Build system prompt
        system_parts = []
        if instructions: system_parts.append(instructions)
        if context: system_parts.append(f"Context: {context}")
        if user_info: system_parts.append(f"User Info: {user_info}")
        if tools: system_parts.append(f"Tools: {', '.join(tools)}")
        if wrapper_model:
            system_parts.append("Respond only with JSON conforming to this schema:")
            system_parts.append(json.dumps(wrapper_model.model_json_schema(), indent=2))
        system_prompt = "\n".join(system_parts) or "You are a helpful assistant."

        # Format messages
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for turn in history.split("\n"):
                if turn.startswith("User:"):
                    messages.append({"role": "user", "content": turn[5:].strip()})
                elif turn.startswith("Assistant:"):
                    messages.append({"role": "assistant", "content": turn[10:].strip()})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=options.get("temperature", 0.0),
                max_tokens=options.get("max_tokens", 1000)
            )
            output = resp.choices[0].message.content.strip()
            if output.startswith("```json"):
                output = output[8:-3].strip()  # Remove ```json and closing ```
            
            if wrapper_model:
                if isinstance(output, str):
                    try:
                        # parse to dict/list first
                        output = json.loads(output)
                    except json.JSONDecodeError as e:
                        raise RuntimeError(f"Invalid JSON output: {e}\n\nRaw output:\n{output}")
                
                # validate using model_validate, not model_validate_json
                parsed = wrapper_model.model_validate(output)
                #print(f"Parsed output: {parsed}")

                # Fix: Properly handle RootModel unwrapping
                if is_list_response:
                    # For RootModel[List[T]], access the root value correctly
                    if hasattr(parsed, 'root'):
                        return parsed.root
                    elif hasattr(parsed, '__root__'):
                        return parsed.__root__
                    else:
                        # Fallback: if it's already a list, return as-is
                        return parsed if isinstance(parsed, list) else [parsed]
                else:
                    return parsed

            return output

        except Exception as e:
            #print(f"Error generating text: {e}")
            return str(e)
    def generate_image(self, prompt: str) -> Image.Image:
        gen = self.client.images.generate(
            model=IMAGE_GEN_MODEL,
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="high"
        )
        url = gen.data[0].url
        img_bytes = requests.get(url).content
        return Image.open(BytesIO(img_bytes))
