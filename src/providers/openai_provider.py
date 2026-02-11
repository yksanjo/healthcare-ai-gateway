"""
OpenAI Provider Adapter
HIPAA Status: NOT COMPLIANT - OpenAI does not sign BAAs
Use only for non-PHI tasks
"""

from typing import AsyncIterator, List
import openai
import time

from .base import BaseProvider, ProviderType, ProviderRequest, ProviderResponse


# Pricing per 1K tokens (as of 2026 - update as needed)
OPENAI_PRICING = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider adapter
    
    ⚠️  HIPAA WARNING: OpenAI does NOT sign Business Associate Agreements.
    This provider should NEVER be used for PHI or HIPAA-regulated data.
    Use only for: general admin, public information, non-clinical tasks.
    """
    
    def __init__(self, api_key: str, default_model: str = "gpt-4o"):
        super().__init__(api_key, default_model)
        self._client: openai.AsyncOpenAI | None = None
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    @property
    def hipaa_compliant(self) -> bool:
        return False  # OpenAI does not sign BAAs
    
    @property
    def baa_available(self) -> bool:
        return False
    
    async def initialize(self):
        """Initialize OpenAI client"""
        self._client = openai.AsyncOpenAI(api_key=self.api_key)
    
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Generate completion via OpenAI"""
        if not self._client:
            await self.initialize()
        
        start_time = time.time()
        model = request.model or self.default_model
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            content = response.choices[0].message.content or ""
            tokens_input = response.usage.prompt_tokens if response.usage else 0
            tokens_output = response.usage.completion_tokens if response.usage else 0
            
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
                    "finish_reason": response.choices[0].finish_reason,
                    "system_fingerprint": response.system_fingerprint,
                    "hipaa_warning": "OpenAI not HIPAA compliant - no BAA",
                },
                raw_response=response,
            )
            
        except openai.RateLimitError as e:
            raise ProviderError(f"OpenAI rate limit exceeded: {e}") from e
        except openai.AuthenticationError as e:
            raise ProviderError(f"OpenAI authentication failed: {e}") from e
        except Exception as e:
            raise ProviderError(f"OpenAI request failed: {e}") from e
    
    async def generate_stream(self, request: ProviderRequest) -> AsyncIterator[str]:
        """Stream completion tokens"""
        if not self._client:
            await self.initialize()
        
        model = request.model or self.default_model
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        stream = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def estimate_cost(self, tokens_input: int, tokens_output: int, model: str) -> float:
        """Calculate estimated cost in USD"""
        pricing = OPENAI_PRICING.get(model, OPENAI_PRICING["gpt-4o"])
        input_cost = (tokens_input / 1000) * pricing["input"]
        output_cost = (tokens_output / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)
    
    def get_available_models(self) -> List[str]:
        """Return available OpenAI models"""
        return list(OPENAI_PRICING.keys())


class ProviderError(Exception):
    """Provider-specific error"""
    pass