"""
Anthropic Provider Adapter
HIPAA Status: COMPLIANT (with BAA) - Recommended for healthcare
"""

from typing import AsyncIterator, List
import anthropic
import time

from .base import BaseProvider, ProviderType, ProviderRequest, ProviderResponse


# Pricing per 1K tokens (as of 2026 - update as needed)
ANTHROPIC_PRICING = {
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
}


class AnthropicProvider(BaseProvider):
    """
    Anthropic provider adapter
    
    ✅ HIPAA COMPLIANT: Anthropic signs Business Associate Agreements
    Zero data retention available with BAA
    Recommended for all healthcare use cases including PHI
    """
    
    def __init__(self, api_key: str, default_model: str = "claude-3-opus-20240229"):
        super().__init__(api_key, default_model)
        self._client: anthropic.AsyncAnthropic | None = None
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC
    
    @property
    def hipaa_compliant(self) -> bool:
        return True  # With signed BAA
    
    @property
    def baa_available(self) -> bool:
        return True
    
    async def initialize(self):
        """Initialize Anthropic client"""
        self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
    
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Generate completion via Anthropic"""
        if not self._client:
            await self.initialize()
        
        start_time = time.time()
        model = request.model or self.default_model
        
        # Build messages
        messages = [{"role": "user", "content": request.prompt}]
        
        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system_prompt,
                messages=messages,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            content = response.content[0].text if response.content else ""
            tokens_input = response.usage.input_tokens if response.usage else 0
            tokens_output = response.usage.output_tokens if response.usage else 0
            
            return ProviderResponse(
                content=content,
                model=model,
                provider=self.provider_type,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                tokens_total=tokens_input + tokens_output,
                latency_ms=latency_ms,
                cost_usd=self.estimate_cost(tokens_input, tokens_output, model),
                metadata={
                    "stop_reason": response.stop_reason,
                    "stop_sequence": response.stop_sequence,
                    "hipaa_status": "compliant_with_baa",
                    "zero_retention": True,
                },
                raw_response=response,
            )
            
        except anthropic.RateLimitError as e:
            raise ProviderError(f"Anthropic rate limit exceeded: {e}") from e
        except anthropic.AuthenticationError as e:
            raise ProviderError(f"Anthropic authentication failed: {e}") from e
        except anthropic.APIError as e:
            raise ProviderError(f"Anthropic API error: {e}") from e
        except Exception as e:
            raise ProviderError(f"Anthropic request failed: {e}") from e
    
    async def generate_stream(self, request: ProviderRequest) -> AsyncIterator[str]:
        """Stream completion tokens"""
        if not self._client:
            await self.initialize()
        
        model = request.model or self.default_model
        
        messages = [{"role": "user", "content": request.prompt}]
        
        async with self._client.messages.stream(
            model=model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=request.system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    def estimate_cost(self, tokens_input: int, tokens_output: int, model: str) -> float:
        """Calculate estimated cost in USD"""
        pricing = ANTHROPIC_PRICING.get(model, ANTHROPIC_PRICING["claude-3-opus-20240229"])
        input_cost = (tokens_input / 1000) * pricing["input"]
        output_cost = (tokens_output / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)
    
    def get_available_models(self) -> List[str]:
        """Return available Anthropic models"""
        return list(ANTHROPIC_PRICING.keys())


class ProviderError(Exception):
    """Provider-specific error"""
    pass