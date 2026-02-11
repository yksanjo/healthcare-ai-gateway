"""
Base Provider Interface
All LLM providers must implement this interface for HIPAA-compliant gateway
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, AsyncIterator
from enum import Enum
import time


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class ProviderResponse:
    """Standardized response across all providers"""
    content: str
    model: str
    provider: ProviderType
    tokens_input: int
    tokens_output: int
    tokens_total: int
    latency_ms: float
    cost_usd: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider.value,
            "tokens": {
                "input": self.tokens_input,
                "output": self.tokens_output,
                "total": self.tokens_total,
            },
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "metadata": self.metadata,
        }


@dataclass
class ProviderRequest:
    """Standardized request across all providers"""
    prompt: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.1  # Lower for healthcare consistency
    max_tokens: int = 4096
    context: Optional[Dict[str, Any]] = None  # HIPAA context, patient info, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "context": self.context,
        }


class BaseProvider(ABC):
    """Abstract base class for all LLM providers"""
    
    def __init__(self, api_key: str, default_model: str):
        self.api_key = api_key
        self.default_model = default_model
        self._client = None
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type enum"""
        pass
    
    @property
    @abstractmethod
    def hipaa_compliant(self) -> bool:
        """Whether this provider can handle PHI under HIPAA"""
        pass
    
    @property
    @abstractmethod
    def baa_available(self) -> bool:
        """Whether Business Associate Agreement is available"""
        pass
    
    @abstractmethod
    async def initialize(self):
        """Initialize the provider client"""
        pass
    
    @abstractmethod
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Generate completion - core method all providers must implement"""
        pass
    
    @abstractmethod
    async def generate_stream(self, request: ProviderRequest) -> AsyncIterator[str]:
        """Stream completion tokens"""
        pass
    
    @abstractmethod
    def estimate_cost(self, tokens_input: int, tokens_output: int, model: str) -> float:
        """Estimate cost in USD for given token counts"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Return list of available models"""
        pass
    
    def _sanitize_for_logging(self, text: str) -> str:
        """Sanitize text for audit logs - remove potential PHI"""
        # Basic sanitization - in production, use proper PHI detection
        return text[:100] + "... [truncated for audit]" if len(text) > 100 else text