import json
from pydantic import RootModel
from openai import OpenAI, RateLimitError
from typing import Optional, List, Dict, Type, get_origin, get_args
from pydantic import BaseModel
from PIL import Image
import os
from .llm_interface import LLMInterface
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
# openai/gpt-oss-120b is the higher-quality alternative with the same built-in
# agentic tools (browser_search, code_interpreter); swap via env if needed.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


class GroqLLM(LLMInterface):
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or GROQ_API_KEY
        if not api_key:
            raise ValueError("Groq API key is required to initialize GroqLLM")

        self.client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        self.model = GROQ_MODEL

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
            # Only named, known kwargs are forwarded here (never `**options`),
            # so an unsupported param like `logprobs` can never reach Groq's
            # OpenAI-compatible endpoint through this path.
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=options.get("temperature", 0.0),
                max_tokens=options.get("max_tokens", 1000),
            )
            output = resp.choices[0].message.content.strip()
            if output.startswith("```json"):
                output = output[8:-3].strip()  # Remove ```json and closing ```

            if wrapper_model:
                if isinstance(output, str):
                    try:
                        # parse to dict/list first. strict=False tolerates raw
                        # control characters (e.g. literal newlines) inside
                        # string values, which Llama models on Groq routinely
                        # emit instead of escaping as \n.
                        output = json.loads(output, strict=False)
                    except json.JSONDecodeError as e:
                        raise RuntimeError(f"Invalid JSON output: {e}\n\nRaw output:\n{output}")

                # validate using model_validate, not model_validate_json
                parsed = wrapper_model.model_validate(output)

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

        except RateLimitError as e:
            raise RuntimeError(
                f"Groq rate limit hit (model={self.model}): {e}. Groq's free-tier "
                "limits are per-organization, not per-key, so this can happen under "
                "concurrent load even if this specific key is under quota."
            ) from e
        except Exception as e:
            raise RuntimeError(f"Groq generation failed: {e}") from e

    def generate_image(self, prompt: str) -> Image.Image:
        raise NotImplementedError("Groq does not support image generation.")
