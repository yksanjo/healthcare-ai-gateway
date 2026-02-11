"""
Healthcare AI Gateway - Configuration
HIPAA-compliant AI orchestration layer
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings with HIPAA-focused defaults"""
    
    # App Configuration
    app_name: str = "Healthcare AI Gateway"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, description="Never True in production for HIPAA")
    
    # API Keys (loaded from environment)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Default model selections by compliance tier
    default_model_openai: str = "gpt-4o"
    default_model_anthropic: str = "claude-3-opus-20240229"
    
    # HIPAA High-Compliance Models (zero retention, BAA available)
    hipaa_compliant_models: List[str] = Field(
        default=[
            "claude-3-opus-20240229",  # Anthropic offers BAA
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
        description="Models with HIPAA Business Associate Agreements"
    )
    
    # Redis Configuration (for rate limiting and caching)
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Database Configuration (encrypted at rest required for HIPAA)
    database_url: str = Field(
        default="postgresql+asyncpg://user:pass@localhost/healthcare_gateway",
        env="DATABASE_URL"
    )
    
    # Audit Logging (immutable, encrypted storage required)
    audit_log_path: str = Field(default="/var/log/healthcare-gateway/audit")
    audit_retention_days: int = Field(default=2555, description="7 years for HIPAA")  # 7 years
    
    # Security
    encryption_key: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")
    jwt_secret: str = Field(default="change-me-in-production", env="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 8
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10
    
    # MCP Configuration
    mcp_server_enabled: bool = True
    mcp_tool_timeout_seconds: int = 30
    mcp_max_tools_per_request: int = 10
    
    # Provider Routing Defaults
    default_provider: str = "anthropic"  # Safer default for healthcare
    fallback_enabled: bool = False  # Disabled by default for compliance
    
    # Risk Scoring Thresholds
    max_hallucination_risk: float = 0.3
    max_compliance_risk: float = 0.1
    require_human_review_threshold: float = 0.7
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


# HIPAA Compliance Configuration
HIPAA_CONFIG = {
    "required_audit_fields": [
        "timestamp",
        "user_id",
        "patient_id_hash",  # Hashed, not plain
        "action",
        "model_used",
        "provider",
        "data_classification",
        "compliance_status",
        "ip_address",
        "session_id",
    ],
    "phi_indicators": [
        "patient",
        "medical_record",
        "ssn",
        "date_of_birth",
        "diagnosis",
        "treatment",
        "medication",
        "provider_name",
    ],
    "allowed_data_classifications": [
        "public",
        "internal",
        "confidential",
        "phi",
        "restricted",
    ],
    "baas_required_for": ["phi", "restricted"],
    "encryption_required_for": ["phi", "restricted", "confidential"],
}


# Provider-Specific HIPAA Compliance Notes
PROVIDER_HIPAA_STATUS = {
    "openai": {
        "baa_available": False,  # As of 2026, OpenAI does not sign BAAs
        "zero_retention": False,
        "hipaa_compliant": False,
        "allowed_for_phi": False,
        "notes": "OpenAI does not sign BAAs. Use only for non-PHI tasks.",
    },
    "anthropic": {
        "baa_available": True,  # Anthropic signs BAAs for enterprise
        "zero_retention": True,  # With BAA
        "hipaa_compliant": True,  # With BAA
        "allowed_for_phi": True,  # With BAA
        "notes": "HIPAA-compliant with signed BAA. Zero data retention available.",
    },
}