# Defines the LLMInterface (standard rules)
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Type
from PIL import Image
from pydantic import BaseModel

class LLMInterface(ABC):

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        context: Optional[str] = "",
        history: Optional[str] = "",
        options: Optional[Dict] = None,
        user_info: Optional[str] = "",
        instructions: Optional[str] = "",
        tools: Optional[List[str]] = None,
        image: Optional[Image.Image] = None,
    ) -> BaseModel | str:
        pass

    @abstractmethod
    def generate_image(self, prompt: str) -> Image:
        pass

from .openai import AzureOpenAILLM
from .gemini import GeminiLLM
from .claude import ClaudeLLM

SUPPORTED_MODELS = ["GEMINI", "OPENAI", "CLAUDE"]

def get_llm(model, api_key: Optional[str] = None) -> LLMInterface:
    # check if the model is supported using a capitalized name
    model = model.upper() if model is not None else "GEMINI"
    if model == "OPENAI":
        return AzureOpenAILLM(api_key=api_key)
    elif model == "GEMINI":
        return GeminiLLM(api_key=api_key)
    elif model in ("CLAUDE", "ANTHROPIC"):
        return ClaudeLLM(api_key=api_key)
    raise NotImplementedError(f"Model {model} not supported. Supported models: {', '.join(SUPPORTED_MODELS)}.")
