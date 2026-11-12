"""SpirandeliEmpire OS 3.1 — Model Provider Base Interface"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""
    finish_reason: Optional[str] = None


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.4,
        tools: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> LLMResponse:
        """Generate response from LLM."""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate or count tokens."""
        pass

