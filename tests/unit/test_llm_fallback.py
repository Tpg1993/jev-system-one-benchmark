import pytest
from unittest.mock import AsyncMock
from src.llm.base import BaseLLMClient, LLMResponse
from src.llm.resilient_gateway import ResilientLLMGateway


class _SarvamStub(BaseLLMClient):
    @property
    def provider_name(self): return "sarvam"
    @property
    def model_name(self): return "sarvam-105b"

    async def generate(self, prompt, system_prompt="", temperature=0.7, max_tokens=512):
        return LLMResponse(
            content="Sarvam AI baseline response.",
            provider="sarvam", model="sarvam-105b",
            total_latency_ms=520.0,
            jev_active=False, fallback_triggered=False,
        )

    async def stream_generate(self, prompt, system_prompt="", temperature=0.7, max_tokens=512):
        yield None


class _OpenAIStub(BaseLLMClient):
    @property
    def provider_name(self): return "openai"
    @property
    def model_name(self): return "gpt-4o"

    async def generate(self, prompt, system_prompt="", temperature=0.7, max_tokens=512):
        return LLMResponse(
            content="OpenAI fallback response.",
            provider="openai", model="gpt-4o",
            total_latency_ms=620.0,
            jev_active=False, fallback_triggered=True,
        )

    async def stream_generate(self, prompt, system_prompt="", temperature=0.7, max_tokens=512):
        yield None


@pytest.mark.asyncio
async def test_resilient_gateway_uses_sarvam_by_default():
    gw = ResilientLLMGateway(primary_client=_SarvamStub(), fallback_client=_OpenAIStub())
    resp = await gw.execute("Test prompt")
    assert resp.provider == "sarvam"
    assert resp.fallback_triggered is False


@pytest.mark.asyncio
async def test_resilient_gateway_falls_back_to_openai_on_sarvam_error():
    failing = _SarvamStub()
    failing.generate = AsyncMock(side_effect=RuntimeError("Sarvam 429 Rate Limited"))
    gw = ResilientLLMGateway(primary_client=failing, fallback_client=_OpenAIStub())
    resp = await gw.execute("Test prompt")
    assert resp.provider == "openai"
    assert resp.fallback_triggered is True
    assert "Rate Limited" in resp.metadata["fallback_reason"]
