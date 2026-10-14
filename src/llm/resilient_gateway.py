import logging
from typing import Optional
from src.llm.base import BaseLLMClient, LLMResponse
from src.llm.sarvam_client import SarvamAIClient
from src.llm.openai_fallback import OpenAIFallbackClient

logger = logging.getLogger("resilient_gateway")


class ResilientLLMGateway:
    """
    Dispatcher: Primary (Sarvam AI 105B) → Fallback (OpenAI).
    Guarantees transparent failover on 429, 5xx, and timeouts.
    """
    def __init__(
        self,
        primary_client: Optional[BaseLLMClient] = None,
        fallback_client: Optional[BaseLLMClient] = None,
    ):
        self.primary = primary_client or SarvamAIClient()
        self.fallback = fallback_client or OpenAIFallbackClient()

    async def execute(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 512,
        force_fallback: bool = False,
    ) -> LLMResponse:
        if force_fallback:
            logger.warning("Forced fallback to OpenAI.")
            return await self.fallback.generate(prompt, system_prompt, temperature, max_tokens)

        try:
            logger.info("Dispatching to primary: %s (%s)", self.primary.provider_name, self.primary.model_name)
            return await self.primary.generate(prompt, system_prompt, temperature, max_tokens)

        except Exception as primary_error:
            logger.error(
                "Primary (%s) failed: %s. Falling back to %s.",
                self.primary.provider_name,
                str(primary_error),
                self.fallback.provider_name,
            )
            try:
                response = await self.fallback.generate(prompt, system_prompt, temperature, max_tokens)
                response.fallback_triggered = True
                response.metadata["fallback_reason"] = str(primary_error)
                return response
            except Exception as fallback_error:
                logger.critical("Both providers failed. Primary: %s | Fallback: %s", primary_error, fallback_error)
                raise RuntimeError(f"LLM Gateway Failure: {primary_error} | {fallback_error}") from fallback_error
