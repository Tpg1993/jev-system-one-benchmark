import time
import httpx
from typing import AsyncGenerator
from src.config import settings
from src.llm.base import BaseLLMClient, LLMResponse, StreamChunk

# Sarvam AI pricing estimate (per 1M tokens)
# Adjust when official pricing is published
_SARVAM_COST_PER_1M_INPUT_TOKENS = 0.40
_SARVAM_COST_PER_1M_OUTPUT_TOKENS = 1.20


class SarvamAIClient(BaseLLMClient):
    """
    Primary LLM Client: Sarvam AI (105B).
    Invoked DIRECTLY (no JEV acceleration) — models the baseline raw latency
    and cost of sending prompts cold to the upstream model server.
    """
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model_name: str = None,
        timeout: float = None,
    ):
        self._api_key = api_key or settings.SARVAM_API_KEY
        self._base_url = (base_url or settings.SARVAM_BASE_URL).rstrip("/")
        self._model_name = model_name or settings.SARVAM_MODEL_NAME
        self._timeout = timeout or settings.SARVAM_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "sarvam"

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "api-subscription-key": self._api_key,
        }

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        input_cost = (prompt_tokens / 1_000_000) * _SARVAM_COST_PER_1M_INPUT_TOKENS
        output_cost = (completion_tokens / 1_000_000) * _SARVAM_COST_PER_1M_OUTPUT_TOKENS
        return round(input_cost + output_cost, 8)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> LLMResponse:
        # Demo simulation when no real API key is configured
        if not self._api_key:
            import asyncio
            await asyncio.sleep(0.15)
            prompt_tokens = len(prompt.split()) + len(system_prompt.split()) + 20
            completion_tokens = 70
            return LLMResponse(
                content=f"[Sarvam AI 105B Reasoning — Baseline] Response for: '{prompt[:60]}...'",
                provider=self.provider_name,
                model=self._model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_latency_ms=520.0,
                estimated_cost_usd=self._estimate_cost(prompt_tokens, completion_tokens),
                jev_active=False,
                fallback_triggered=False,
                metadata={"demo_mode": True},
            )

        start_time = time.perf_counter()
        messages = []
        if system_prompt:
            if "conversations" in self._model_name.lower():
                messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
            else:
                messages.append({"role": "user", "content": f"{system_prompt}\n\n{prompt}"})
        else:
            messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

        total_latency_ms = (time.perf_counter() - start_time) * 1000
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        # Sarvam 105B is a reasoning model: content may be null;
        # fall back to reasoning_content (chain-of-thought output)
        content = (
            msg.get("content")
            or msg.get("reasoning_content")
            or ""
        )
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", len(prompt.split()))
        completion_tokens = usage.get("completion_tokens", len((content or "").split()))

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_latency_ms=total_latency_ms,
            estimated_cost_usd=self._estimate_cost(prompt_tokens, completion_tokens),
            jev_active=False,
            fallback_triggered=False,
            metadata={"finish_reason": choice.get("finish_reason")},
        )

    async def stream_generate(
        self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 512
    ) -> AsyncGenerator[StreamChunk, None]:
        messages = []
        if system_prompt:
            if "conversations" in self._model_name.lower():
                messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
            else:
                messages.append({"role": "user", "content": f"{system_prompt}\n\n{prompt}"})
        else:
            messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        start_time = time.perf_counter()
        is_first = True
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", f"{self._base_url}/chat/completions", json=payload, headers=self._get_headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk_time = (time.perf_counter() - start_time) * 1000
                        yield StreamChunk(delta_content=line[6:], is_first_token=is_first, timestamp_ms=chunk_time)
                        is_first = False
