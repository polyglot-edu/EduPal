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
        context: Optional[str] = "",
        history: Optional[str] = "",
        options: Optional[Dict] = None,
        user_info: Optional[str] = "",
    ) -> str:
        pass

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        context: Optional[str] = "",
        history: Optional[str] = "",
        options: Optional[Dict] = None,
        user_info: Optional[str] = "",
    ) -> BaseModel:
        pass

    @abstractmethod
    def generate_image(self, prompt: str) -> Image:
        pass
