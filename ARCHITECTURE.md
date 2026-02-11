# Healthcare AI Gateway - Technical Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HEALTHCARE AI GATEWAY                            │
│                    (Your Compliance Certification Layer)                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     API Layer (FastAPI)                          │    │
│  │  POST /generate  │  GET /health  │  GET /compliance/report      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   Governance & Compliance Layer                  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │    │
│  │  │Policy Engine │  │ Risk Engine  │  │   Audit Logger       │   │    │
│  │  │              │  │              │  │   (HIPAA-compliant)  │   │    │
│  │  │ • YAML rules │  │ • Hallucin.  │  │   • Immutable        │   │    │
│  │  │ • PHI detect │  │ • Compliance │  │   • Tamper-evident   │   │    │
│  │  │ • HIPAA rout │  │ • Data leak  │  │   • 7-year retention │   │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │    │
│  │         │                 │                     │                │    │
│  │         └─────────────────┼─────────────────────┘                │    │
│  │                           │                                       │    │
│  │              ┌────────────┴────────────┐                         │    │
│  │              │    Routing Decision     │                         │    │
│  │              │  Provider + Model + Risk│                         │    │
│  │              └────────────┬────────────┘                         │    │
│  └───────────────────────────┼─────────────────────────────────────┘    │
│                              │                                           │
│  ┌───────────────────────────┼─────────────────────────────────────┐    │
│  │              Provider Abstraction Layer                         │    │
│  │  ┌────────────────────┐   │   ┌────────────────────┐            │    │
│  │  │   OpenAI Adapter   │◄──┘   │ Anthropic Adapter  │            │    │
│  │  │                    │       │                    │            │    │
│  │  │  Model: GPT-4o     │       │ Model: Claude Opus │            │    │
│  │  │  HIPAA: ❌ No BAA  │       │ HIPAA: ✅ BAA      │            │    │
│  │  │  PHI: ❌ Blocked   │       │ PHI: ✅ Allowed    │            │    │
│  │  │  Use: Admin only   │       │ Use: Clinical      │            │    │
│  │  └────────────────────┘       └────────────────────┘            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Policy Engine (`src/policy/engine.py`)

**Purpose:** Deterministic compliance decisions based on configurable rules

**Key Classes:**
- `PolicyEngine` - Main rule evaluation engine
- `PolicyRule` - Individual rule definition
- `RoutingDecision` - Output with provider selection

**Built-in Rules:**
1. `phi_requires_hipaa_provider` - PHI → Anthropic only
2. `healthcare_industry_restrictions` - Extra logging for healthcare
3. `financial_services_compliance` - SOX requirements
4. `high_risk_human_review` - Risk > 0.7 → human review
5. `public_data_cost_optimization` - Public → any provider

**Extensibility:** Load custom rules from `config/policies.yaml`

### 2. Risk Engine (`src/risk/engine.py`)

**Purpose:** Vendor-agnostic quality and safety assessment

**Key Classes:**
- `RiskEngine` - Main analysis engine
- `RiskScore` - Comprehensive risk metrics

**Risk Dimensions:**
- **Hallucination Risk** (0-1): Likelihood of false information
- **Compliance Risk** (0-1): HIPAA/regulatory violation potential
- **Data Leakage Risk** (0-1): PHI exposure in output
- **Cultural Sensitivity Risk** (0-1): Bias/unethical content
- **Overall Risk** (0-1): Weighted composite

**Why This Creates Leverage:**
You become the independent scorekeeper. Vendors compete to rank higher.

### 3. Audit Logger (`src/audit/logger.py`)

**Purpose:** HIPAA-compliant immutable audit trail

**Key Features:**
- **Tamper-evident:** SHA-256 hash chain
- **Privacy-safe:** Identifiers hashed, prompts not stored raw
- **7-year retention:** HIPAA requirement
- **Integrity verification:** `verify_integrity()` method

**Audit Record Fields:**
```json
{
  "timestamp": "2026-02-11T18:30:00Z",
  "request_id": "req_abc123",
  "user_hash": "a1b2c3d4...",
  "prompt_hash": "e5f6g7h8...",
  "routing": {
    "provider": "anthropic",
    "model": "claude-3-opus-20240229",
    "compliance_status": "approved"
  },
  "response": {
    "tokens_input": 150,
    "tokens_output": 300,
    "cost_usd": 0.02475
  },
  "risk": {
    "overall": 0.25,
    "flags": ["REQUIRES_HUMAN_REVIEW"]
  },
  "audit_hash": "sha256_hash...",
  "previous_hash": "previous_sha256..."
}
```

### 4. Provider Adapters

#### OpenAI Provider (`src/providers/openai_provider.py`)
```python
class OpenAIProvider(BaseProvider):
    hipaa_compliant = False  # No BAA available
    baa_available = False
    
    # Use only for:
    # - Administrative tasks
    # - Public information
    # - Non-clinical workflows
```

#### Anthropic Provider (`src/providers/anthropic_provider.py`)
```python
class AnthropicProvider(BaseProvider):
    hipaa_compliant = True   # With signed BAA
    baa_available = True
    
    # Use for:
    # - PHI handling
    # - Clinical decision support
    # - All healthcare workflows
```

## Data Flow

```
1. REQUEST RECEIVED
   POST /generate
   {
     "prompt": "...",
     "industry": "healthcare",
     "data_classification": "phi"
   }
         ↓
2. POLICY EVALUATION
   PolicyEngine.evaluate(context)
   - Check rules by priority
   - Determine allowed providers
   - Select best provider/model
         ↓
3. PROVIDER EXECUTION
   Provider.generate(request)
   - Call OpenAI or Anthropic API
   - Normalize response
   - Calculate cost
         ↓
4. RISK ANALYSIS
   RiskEngine.analyze(output, context)
   - Score hallucination risk
   - Check compliance
   - Detect PHI leakage
         ↓
5. AUDIT LOGGING
   AuditLogger.log_request(...)
   - Create tamper-evident record
   - Hash chain for integrity
   - Async write to storage
         ↓
6. RESPONSE
   {
     "content": "...",
     "provider": "anthropic",
     "compliance_status": "approved",
     "requires_human_review": true,
     "risk_scores": {...}
   }
```

## Security Architecture

### Authentication (To Implement for Production)
```python
# Current: Bearer token (simplified)
# Production: JWT with RBAC

class Authentication:
    - JWT validation
    - Role-based access (admin, clinician, auditor)
    - Session management
    - MFA for PHI access
```

### Data Protection
```
┌─────────────────────────────────────────┐
│           Data Classification           │
├─────────────────────────────────────────┤
│ PUBLIC       │ No encryption required   │
│ INTERNAL     │ TLS in transit           │
│ CONFIDENTIAL │ TLS + encryption at rest │
│ PHI          │ TLS + encryption at rest │
│              │ + access logging         │
│              │ + BAA required           │
│ RESTRICTED   │ TLS + encryption at rest │
│              │ + tokenization           │
└─────────────────────────────────────────┘
```

### Audit Security
- Immutable logs (append-only)
- Hash chain prevents tampering
- Separate storage from application
- Encrypted at rest
- 7-year retention with verification

## Scalability Considerations

### Horizontal Scaling
```
┌─────────────────────────────────────────┐
│           Load Balancer                 │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┐
    ↓         ↓         ↓
┌───────┐ ┌───────┐ ┌───────┐
│GW-1   │ │GW-2   │ │GW-3   │  # Stateless API instances
└───┬───┘ └───┬───┘ └───┬───┘
    │         │         │
    └─────────┼─────────┘
              ↓
    ┌─────────────────────┐
    │   Redis Cluster     │  # Shared state (rate limits)
    └─────────────────────┘
              ↓
    ┌─────────────────────┐
    │  PostgreSQL Primary │  # Audit logs, config
    │  + Read Replicas    │
    └─────────────────────┘
```

### Caching Strategy
- **Rate limits:** Redis (fast, distributed)
- **Provider responses:** No caching (compliance)
- **Policy rules:** In-memory (read-heavy)
- **Risk scores:** No caching (must be fresh)

## Deployment Architecture

### Development
```bash
uvicorn src.main:app --reload
```

### Production (Docker)
```yaml
# docker-compose.yml
version: '3.8'
services:
  gateway:
    build: .
    ports:
      - "443:443"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    volumes:
      - /secure/audit:/var/log/healthcare-gateway/audit
  
  redis:
    image: redis:7-alpine
    
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: healthcare_gateway
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Kubernetes (Future)
- Horizontal Pod Autoscaler
- PodDisruptionBudget for availability
- NetworkPolicy for segmentation
- Secrets management (Vault)

## Monitoring & Observability

### Metrics to Track
| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Request latency | API | p99 > 5s |
| Error rate | API | > 1% |
| Provider failovers | Router | Any failure |
| PHI detection rate | Policy | Monitor trend |
| Risk score > 0.7 | Risk Engine | Immediate |
| Audit log integrity | Audit | Any failure |

### Structured Logging
```json
{
  "timestamp": "2026-02-11T18:30:00Z",
  "level": "info",
  "event": "request_completed",
  "request_id": "req_abc123",
  "provider": "anthropic",
  "latency_ms": 1200,
  "risk_overall": 0.25
}
```

## Extension Points

### Adding a New Provider
```python
# 1. Create adapter in src/providers/new_provider.py
class NewProvider(BaseProvider):
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.NEW
    
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        # Implementation
        pass

# 2. Add to ProviderFactory
# 3. Update HIPAA status in config
# 4. Add tests
```

### Adding a New Policy Rule
```yaml
# config/policies.yaml
rules:
  - name: my_custom_rule
    priority: 75
    conditions:
      industry: healthcare
      custom_field: value
    actions:
      allowed_providers: ["anthropic"]
```

### Adding a New Risk Dimension
```python
# In RiskEngine class
def _assess_new_risk(self, text: str, context: dict) -> float:
    # Implementation
    return risk_score
```

## Files Reference

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI application, endpoints |
| `src/config.py` | Settings, HIPAA config |
| `src/policy/engine.py` | Policy evaluation |
| `src/risk/engine.py` | Risk scoring |
| `src/audit/logger.py` | Audit logging |
| `src/providers/base.py` | Provider interface |
| `src/providers/openai_provider.py` | OpenAI integration |
| `src/providers/anthropic_provider.py` | Anthropic integration |
| `src/providers/factory.py` | Provider instantiation |
| `config/policies.yaml` | Custom rules |

## Next Technical Steps

1. **Install dependencies:** `pip install -r requirements.txt`
2. **Configure environment:** `cp .env.example .env && edit`
3. **Run demo:** `python demo.py`
4. **Start server:** `uvicorn src.main:app --reload`
5. **Test endpoint:** `curl -X POST http://localhost:8000/generate ...`
6. **Add tests:** `pytest tests/`
7. **Dockerize:** `docker build -t healthcare-gateway .`
8. **Deploy:** Kubernetes manifest