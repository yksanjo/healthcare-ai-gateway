"""
Healthcare AI Gateway - Main Application
HIPAA-compliant AI orchestration API
"""

import uuid
import time
import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog

from .config import settings
from .providers import ProviderFactory, ProviderRequest, ProviderType
from .policy import PolicyEngine, DataClassification, Industry
from .risk import RiskEngine
from .audit import AuditLogger

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# Pydantic Models for API
class GenerateRequest(BaseModel):
    """Request model for AI generation"""
    prompt: str = Field(..., min_length=1, max_length=100000, description="The prompt to send to the AI")
    system_prompt: Optional[str] = Field(None, description="Optional system instructions")
    
    # Compliance Context
    industry: Industry = Field(default=Industry.HEALTHCARE, description="Industry for compliance rules")
    data_classification: DataClassification = Field(
        default=DataClassification.INTERNAL,
        description="Data sensitivity level"
    )
    patient_id: Optional[str] = Field(None, description="Hashed patient identifier (optional)")
    
    # Model Configuration
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    
    # Optional override (usually determined by policy)
    preferred_provider: Optional[ProviderType] = Field(None, description="Provider preference (policy may override)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Summarize the key points from this medical research article...",
                "industry": "healthcare",
                "data_classification": "phi",
                "patient_id": "hashed_patient_id_123",
            }
        }


class GenerateResponse(BaseModel):
    """Response model for AI generation"""
    request_id: str
    content: str
    
    # Provider Info
    provider: str
    model: str
    
    # Usage
    tokens: Dict[str, int]
    latency_ms: float
    cost_usd: float
    
    # Compliance
    compliance_status: str
    requires_human_review: bool
    applied_policies: list
    
    # Risk Assessment
    risk_scores: Dict[str, float]
    risk_flags: list
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req_123abc",
                "content": "The research indicates...",
                "provider": "anthropic",
                "model": "claude-3-opus-20240229",
                "tokens": {"input": 150, "output": 300, "total": 450},
                "latency_ms": 1200,
                "cost_usd": 0.02475,
                "compliance_status": "approved",
                "requires_human_review": True,
                "applied_policies": ["phi_requires_hipaa_provider", "healthcare_industry_restrictions"],
                "risk_scores": {
                    "overall": 0.25,
                    "hallucination": 0.15,
                    "compliance": 0.10,
                },
                "risk_flags": ["REQUIRES_HUMAN_REVIEW"],
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    providers: Dict[str, str]
    compliance_mode: str


class ComplianceReport(BaseModel):
    """Compliance status report"""
    gateway_version: str
    total_rules: int
    enabled_rules: int
    provider_status: Dict[str, Any]
    hipaa_configuration: Dict[str, Any]


# Global instances (initialized on startup)
policy_engine: Optional[PolicyEngine] = None
risk_engine: Optional[RiskEngine] = None
audit_logger: Optional[AuditLogger] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global policy_engine, risk_engine, audit_logger
    
    logger.info("Starting Healthcare AI Gateway", version=settings.app_version)
    
    # Initialize engines
    policy_engine = PolicyEngine()
    risk_engine = RiskEngine()
    audit_logger = AuditLogger()
    
    # Initialize providers
    await ProviderFactory.initialize_all()
    
    logger.info("Gateway initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Healthcare AI Gateway")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="HIPAA-compliant AI gateway with intelligent routing between OpenAI and Anthropic",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Security middleware
security = HTTPBearer(auto_error=False)


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify bearer token (simplified - use proper auth in production)"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    # In production: validate JWT, check permissions, etc.
    return credentials.credentials


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    providers = {}
    for provider_type in ProviderType:
        try:
            provider = ProviderFactory.get_provider(provider_type)
            providers[provider_type.value] = "available" if provider else "unavailable"
        except ValueError:
            providers[provider_type.value] = "not_configured"
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        providers=providers,
        compliance_mode="hipaa_strict",
    )


@app.get("/compliance/report", response_model=ComplianceReport)
async def compliance_report():
    """Get compliance configuration report"""
    report = policy_engine.get_compliance_report()
    return ComplianceReport(
        gateway_version=settings.app_version,
        total_rules=report["total_rules"],
        enabled_rules=report["enabled_rules"],
        provider_status=report["provider_status"],
        hipaa_configuration=report["hipaa_config"],
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate(
    request: Request,
    body: GenerateRequest,
    authorization: str = Header(None),
    x_request_id: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
):
    """
    Generate AI completion with HIPAA-compliant routing
    
    This endpoint:
    1. Evaluates compliance policies
    2. Routes to appropriate provider
    3. Scores output for risk
    4. Creates immutable audit log
    """
    start_time = time.time()
    request_id = x_request_id or f"req_{uuid.uuid4().hex[:12]}"
    user_id = x_user_id or "anonymous"
    session_id = x_session_id or "no_session"
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(
        "Request received",
        request_id=request_id,
        user_id=user_id,
        industry=body.industry.value,
        data_classification=body.data_classification.value,
    )
    
    try:
        # Step 1: Build context and evaluate policy
        context = {
            "industry": body.industry.value,
            "data_classification": body.data_classification.value,
            "risk_level": 0.0,  # Will be updated after generation
            "user_id": user_id,
            "session_id": session_id,
        }
        
        routing_decision = policy_engine.evaluate(context)
        
        if not routing_decision.allowed:
            logger.warning(
                "Request rejected by policy",
                request_id=request_id,
                reason=routing_decision.rejection_reason,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Request blocked by compliance policy",
                    "reason": routing_decision.rejection_reason,
                    "applied_rules": routing_decision.applied_rules,
                },
            )
        
        # Step 2: Get provider and generate
        provider = ProviderFactory.get_provider(routing_decision.provider)
        
        provider_request = ProviderRequest(
            prompt=body.prompt,
            system_prompt=body.system_prompt,
            model=routing_decision.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            context=context,
        )
        
        provider_response = await provider.generate(provider_request)
        
        # Step 3: Risk assessment
        risk_score = risk_engine.analyze(provider_response.content, context)
        
        # Step 4: Audit logging (async, non-blocking)
        asyncio.create_task(
            audit_logger.log_request(
                request_id=request_id,
                user_id=user_id,
                session_id=session_id,
                ip_address=client_ip,
                prompt=body.prompt,
                context=context,
                routing_decision=routing_decision,
                provider_response=provider_response,
                risk_score=risk_score,
            )
        )
        
        total_latency = (time.time() - start_time) * 1000
        
        logger.info(
            "Request completed",
            request_id=request_id,
            provider=routing_decision.provider.value,
            model=routing_decision.model,
            latency_ms=total_latency,
            risk_overall=risk_score.overall_risk,
        )
        
        return GenerateResponse(
            request_id=request_id,
            content=provider_response.content,
            provider=routing_decision.provider.value,
            model=routing_decision.model,
            tokens={
                "input": provider_response.tokens_input,
                "output": provider_response.tokens_output,
                "total": provider_response.tokens_total,
            },
            latency_ms=total_latency,
            cost_usd=provider_response.cost_usd,
            compliance_status=routing_decision.compliance_status,
            requires_human_review=routing_decision.requires_human_review or risk_score.overall_risk > 0.5,
            applied_policies=routing_decision.applied_rules,
            risk_scores={
                "overall": risk_score.overall_risk,
                "hallucination": risk_score.hallucination_risk,
                "compliance": risk_score.compliance_risk,
                "data_leakage": risk_score.data_leakage_risk,
                "cultural": risk_score.cultural_sensitivity_risk,
            },
            risk_flags=risk_score.flags,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Request failed",
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal gateway error", "request_id": request_id},
        )


@app.get("/providers")
async def list_providers():
    """List configured providers and their status"""
    providers = {}
    for provider_type in ProviderType:
        try:
            provider = ProviderFactory.get_provider(provider_type)
            providers[provider_type.value] = {
                "configured": True,
                "hipaa_compliant": provider.hipaa_compliant,
                "baa_available": provider.baa_available,
                "available_models": provider.get_available_models(),
            }
        except ValueError as e:
            providers[provider_type.value] = {
                "configured": False,
                "error": str(e),
            }
    
    return {"providers": providers}


# Error handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )