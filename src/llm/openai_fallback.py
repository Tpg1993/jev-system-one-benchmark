import time
from typing import AsyncGenerator
from openai import AsyncOpenAI
from src.config import settings
from src.llm.base import BaseLLMClient, LLMResponse, StreamChunk

_OPENAI_COST_PER_1M_INPUT_TOKENS = 2.50   # gpt-4o
_OPENAI_COST_PER_1M_OUTPUT_TOKENS = 10.00


class OpenAIFallbackClient(BaseLLMClient):
    """
    Fallback LLM Client: OpenAI (gpt-4o).
    Activated automatically when Sarvam AI is unavailable (429, 5xx, timeout).
    """
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model_name: str = None,
        timeout: float = None,
    ):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._base_url = base_url or settings.OPENAI_BASE_URL
        self._model_name = model_name or settings.OPENAI_MODEL_NAME
        self._timeout = timeout or settings.OPENAI_TIMEOUT_SECONDS
        self._client = AsyncOpenAI(
            api_key=self._api_key or "dummy-key-for-initialization",
            base_url=self._base_url,
            timeout=self._timeout,
        )

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return round(
            (prompt_tokens / 1_000_000) * _OPENAI_COST_PER_1M_INPUT_TOKENS
            + (completion_tokens / 1_000_000) * _OPENAI_COST_PER_1M_OUTPUT_TOKENS,
            8,
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> LLMResponse:
        if not self._api_key or self._api_key == "dummy-key-for-initialization":
            import asyncio
            await asyncio.sleep(0.2)
            prompt_tokens = len(prompt.split()) + len(system_prompt.split()) + 20
            completion_tokens = 60
            return LLMResponse(
                content=f"[OpenAI Fallback Demo] Response for: '{prompt[:60]}...'",
                provider=self.provider_name,
                model=self._model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_latency_ms=620.0,
                estimated_cost_usd=self._estimate_cost(prompt_tokens, completion_tokens),
                jev_active=False,
                fallback_triggered=True,
                metadata={"demo_mode": True},
            )

        start_time = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        total_latency_ms = (time.perf_counter() - start_time) * 1000
        choice = response.choices[0]
        content = choice.message.content or ""
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else len(prompt.split())
        completion_tokens = usage.completion_tokens if usage else len(content.split())

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_latency_ms=total_latency_ms,
            estimated_cost_usd=self._estimate_cost(prompt_tokens, completion_tokens),
            jev_active=False,
            fallback_triggered=True,
            metadata={"finish_reason": choice.finish_reason},
        )

    async def stream_generate(
        self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 512
    ) -> AsyncGenerator[StreamChunk, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        start_time = time.perf_counter()
        is_first = True
        stream = await self._client.chat.completions.stream(
            model=self._model_name, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield StreamChunk(
                    delta_content=delta,
                    is_first_token=is_first,
                    timestamp_ms=(time.perf_counter() - start_time) * 1000,
                )
                is_first = False
