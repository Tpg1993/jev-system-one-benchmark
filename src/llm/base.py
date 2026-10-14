from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, Any, Optional


@dataclass
class LLMResponse:
    """
    Unified response schema for both System 1 Decision Models (Jev)
    and System 2 Generative LLMs (Sarvam 105B / OpenAI).
    """
    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0

    # Decision Model vs Generative LLM telemetry
    is_system_one_decision: bool = False
    jev_active: bool = False
    fallback_triggered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    delta_content: str
    is_first_token: bool = False
    timestamp_ms: float = 0.0


class BaseLLMClient(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    async def generate(
        self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 512
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def stream_generate(
        self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 512
    ) -> AsyncGenerator[StreamChunk, None]:
        pass
