"""
Policy Engine - The Core Moat
HIPAA-compliant routing and governance decisions
"""

import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging

from ..providers.base import ProviderType
from ..config import HIPAA_CONFIG, PROVIDER_HIPAA_STATUS, settings

logger = logging.getLogger(__name__)


class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PHI = "phi"
    RESTRICTED = "restricted"


class Industry(str, Enum):
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    LEGAL = "legal"
    GOVERNMENT = "government"
    GENERAL = "general"


@dataclass
class PolicyRule:
    """Individual policy rule"""
    name: str
    description: str
    priority: int  # Higher = evaluated first
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    enabled: bool = True


@dataclass
class RoutingDecision:
    """Result of policy evaluation"""
    provider: ProviderType
    model: str
    allowed: bool
    requires_human_review: bool
    compliance_status: str
    applied_rules: List[str]
    rejection_reason: Optional[str] = None
    risk_threshold: float = 0.0
    additional_metadata: Dict[str, Any] = field(default_factory=dict)


class PolicyEngine:
    """
    HIPAA Policy Engine
    
    Evaluates requests against compliance rules and makes routing decisions.
    This is the core intellectual property that creates vendor leverage.
    """
    
    def __init__(self, rules_file: Optional[str] = None):
        self.rules: List[PolicyRule] = []
        self.default_provider = ProviderType(settings.default_provider)
        self.rules_file = rules_file or "config/policies.yaml"
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load built-in HIPAA compliance rules"""
        
        # Rule 1: PHI Data Must Use HIPAA-Compliant Provider
        self.rules.append(PolicyRule(
            name="phi_requires_hipaa_provider",
            description="PHI data must use providers with signed BAA",
            priority=100,
            conditions={
                "data_classification": [DataClassification.PHI.value, DataClassification.RESTRICTED.value],
            },
            actions={
                "allowed_providers": [ProviderType.ANTHROPIC.value],  # Only Anthropic has BAA
                "forbidden_providers": [ProviderType.OPENAI.value],
                "requires_human_review": True,
                "compliance_note": "HIPAA BAA required for PHI",
            }
        ))
        
        # Rule 2: Healthcare Industry Restrictions
        self.rules.append(PolicyRule(
            name="healthcare_industry_restrictions",
            description="Healthcare industry has specific compliance requirements",
            priority=90,
            conditions={
                "industry": Industry.HEALTHCARE.value,
            },
            actions={
                "allowed_models": settings.hipaa_compliant_models,
                "require_audit_logging": True,
                "encryption_required": True,
                "data_retention": "zero",  # No data retention
            }
        ))
        
        # Rule 3: Financial Services Requirements
        self.rules.append(PolicyRule(
            name="financial_services_compliance",
            description="Financial services require enhanced audit trails",
            priority=85,
            conditions={
                "industry": Industry.FINANCE.value,
            },
            actions={
                "allowed_providers": [ProviderType.ANTHROPIC.value],  # More conservative
                "require_audit_logging": True,
                "retention_days": 2555,  # 7 years for SOX
            }
        ))
        
        # Rule 4: High-Risk Content Requires Review
        self.rules.append(PolicyRule(
            name="high_risk_human_review",
            description="High-risk content classifications require human review",
            priority=80,
            conditions={
                "risk_level": {"min": 0.7},
            },
            actions={
                "requires_human_review": True,
                "alert_compliance_officer": True,
            }
        ))
        
        # Rule 5: Public Data Can Use Any Provider (Cost Optimization)
        self.rules.append(PolicyRule(
            name="public_data_cost_optimization",
            description="Public data can use any provider for cost optimization",
            priority=10,
            conditions={
                "data_classification": DataClassification.PUBLIC.value,
            },
            actions={
                "allowed_providers": [ProviderType.OPENAI.value, ProviderType.ANTHROPIC.value],
                "optimize_for": "cost",  # Can use cheaper models
            }
        ))
        
        # Sort by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def load_rules_from_file(self, filepath: str):
        """Load additional rules from YAML file"""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Rules file not found: {filepath}")
            return
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data or 'rules' not in data:
            return
        
        for rule_data in data['rules']:
            rule = PolicyRule(
                name=rule_data['name'],
                description=rule_data.get('description', ''),
                priority=rule_data.get('priority', 50),
                conditions=rule_data.get('conditions', {}),
                actions=rule_data.get('actions', {}),
                enabled=rule_data.get('enabled', True),
            )
            self.rules.append(rule)
        
        # Re-sort by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Loaded {len(data['rules'])} rules from {filepath}")
    
    def evaluate(self, context: Dict[str, Any]) -> RoutingDecision:
        """
        Evaluate request context against all policies and return routing decision
        
        This is the core method that determines which provider to use.
        """
        applied_rules = []
        allowed_providers = set(ProviderType)
        forbidden_providers = set()
        requires_human_review = False
        allowed_models = None
        compliance_status = "approved"
        rejection_reason = None
        
        # Extract context values
        data_classification = context.get('data_classification', 'internal')
        industry = context.get('industry', 'general')
        risk_level = context.get('risk_level', 0.0)
        
        # Evaluate each rule
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if self._matches_conditions(rule.conditions, context):
                applied_rules.append(rule.name)
                
                # Apply actions
                actions = rule.actions
                
                if 'allowed_providers' in actions:
                    allowed = {ProviderType(p) for p in actions['allowed_providers']}
                    allowed_providers = allowed_providers.intersection(allowed)
                
                if 'forbidden_providers' in actions:
                    forbidden = {ProviderType(p) for p in actions['forbidden_providers']}
                    forbidden_providers.update(forbidden)
                
                if actions.get('requires_human_review'):
                    requires_human_review = True
                
                if 'allowed_models' in actions:
                    allowed_models = actions['allowed_models']
        
        # Remove forbidden providers
        allowed_providers = allowed_providers - forbidden_providers
        
        # Determine final provider
        if not allowed_providers:
            return RoutingDecision(
                provider=self.default_provider,
                model=settings.default_model_anthropic,
                allowed=False,
                requires_human_review=True,
                compliance_status="rejected",
                applied_rules=applied_rules,
                rejection_reason="No compliant providers available for this request context",
            )
        
        # Prefer Anthropic for healthcare (HIPAA compliant)
        if ProviderType.ANTHROPIC in allowed_providers and industry == Industry.HEALTHCARE.value:
            selected_provider = ProviderType.ANTHROPIC
        elif ProviderType.ANTHROPIC in allowed_providers and data_classification in [DataClassification.PHI.value, DataClassification.RESTRICTED.value]:
            selected_provider = ProviderType.ANTHROPIC
        else:
            # Default to first allowed or settings default
            selected_provider = self.default_provider if self.default_provider in allowed_providers else list(allowed_providers)[0]
        
        # Select model
        if allowed_models:
            selected_model = allowed_models[0]  # Use first allowed
        elif selected_provider == ProviderType.ANTHROPIC:
            selected_model = settings.default_model_anthropic
        else:
            selected_model = settings.default_model_openai
        
        return RoutingDecision(
            provider=selected_provider,
            model=selected_model,
            allowed=True,
            requires_human_review=requires_human_review,
            compliance_status=compliance_status,
            applied_rules=applied_rules,
            risk_threshold=risk_level,
            additional_metadata={
                "allowed_providers": [p.value for p in allowed_providers],
                "data_classification": data_classification,
                "industry": industry,
            }
        )
    
    def _matches_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if context matches rule conditions"""
        for key, expected in conditions.items():
            actual = context.get(key)
            
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif isinstance(expected, dict):
                # Handle comparison operators
                if 'min' in expected and (actual is None or actual < expected['min']):
                    return False
                if 'max' in expected and (actual is None or actual > expected['max']):
                    return False
            else:
                if actual != expected:
                    return False
        
        return True
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance configuration report"""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "hipaa_config": HIPAA_CONFIG,
            "provider_status": PROVIDER_HIPAA_STATUS,
            "default_provider": settings.default_provider,
            "hipaa_compliant_models": settings.hipaa_compliant_models,
        }