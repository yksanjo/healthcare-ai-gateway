"""
Provider Factory
Creates and manages provider instances
"""

from typing import Optional, Dict
from .base import BaseProvider, ProviderType
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from ..config import settings


class ProviderFactory:
    """Factory for creating provider instances"""
    
    _instances: Dict[ProviderType, BaseProvider] = {}
    
    @classmethod
    def get_provider(cls, provider_type: ProviderType) -> BaseProvider:
        """Get or create provider instance"""
        if provider_type not in cls._instances:
            cls._instances[provider_type] = cls._create_provider(provider_type)
        return cls._instances[provider_type]
    
    @classmethod
    def _create_provider(cls, provider_type: ProviderType) -> BaseProvider:
        """Create new provider instance"""
        if provider_type == ProviderType.OPENAI:
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                default_model=settings.default_model_openai
            )
        
        elif provider_type == ProviderType.ANTHROPIC:
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            return AnthropicProvider(
                api_key=settings.anthropic_api_key,
                default_model=settings.default_model_anthropic
            )
        
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
    
    @classmethod
    def get_default_provider(cls) -> BaseProvider:
        """Get default provider based on settings"""
        default = ProviderType(settings.default_provider)
        return cls.get_provider(default)
    
    @classmethod
    def get_hipaa_compliant_provider(cls) -> BaseProvider:
        """Get provider that supports HIPAA/PHI"""
        # Anthropic is the only HIPAA-compliant option currently
        return cls.get_provider(ProviderType.ANTHROPIC)
    
    @classmethod
    def get_all_providers(cls) -> Dict[ProviderType, BaseProvider]:
        """Get all configured providers"""
        providers = {}
        if settings.openai_api_key:
            providers[ProviderType.OPENAI] = cls.get_provider(ProviderType.OPENAI)
        if settings.anthropic_api_key:
            providers[ProviderType.ANTHROPIC] = cls.get_provider(ProviderType.ANTHROPIC)
        return providers
    
    @classmethod
    async def initialize_all(cls):
        """Initialize all configured providers"""
        for provider in cls.get_all_providers().values():
            await provider.initialize()
    
    @classmethod
    def reset(cls):
        """Reset all provider instances (useful for testing)"""
        cls._instances = {}