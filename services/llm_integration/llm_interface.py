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
        context: Optional[List[str]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        options: Optional[Dict] = None,
        user_info: Optional[Dict] = None,
    ) -> str:
        pass

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        context: Optional[List[str]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        options: Optional[Dict] = None,
        user_info: Optional[Dict] = None,
    ) -> BaseModel:
        pass

    @abstractmethod
    def generate_image(self, prompt: str) -> Image:
        pass
