# Healthcare AI Gateway

**HIPAA-compliant AI orchestration layer with intelligent routing between OpenAI and Anthropic**

This is a working prototype that demonstrates how to create a compliance-focused AI gateway that creates leverage in the OpenAI vs Anthropic ecosystem by becoming the "certification authority" for regulated enterprise deployment.

## 🎯 Strategic Value Proposition

> "We certify AI outputs for regulated enterprise deployment."

This positioning creates a structural dependency:
- **Enterprises** need compliance certification for AI deployments
- **Vendors** (OpenAI/Anthropic) must integrate with your governance layer to access certified enterprise traffic
- You become the **benchmarking authority** that vendors compete to rank higher in

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    HEALTHCARE AI GATEWAY                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Policy    │  │    Risk     │  │   Audit Logger      │ │
│  │   Engine    │  │   Engine    │  │   (HIPAA-compliant) │ │
│  │  (Your Moat)│  │  (Scoring)  │  │   (Immutable)       │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                     │            │
│         └────────────────┼─────────────────────┘            │
│                          │                                  │
│  ┌───────────────────────┴───────────────────────┐          │
│  │           Provider Router                      │          │
│  │  ┌──────────┐            ┌──────────┐         │          │
│  │  │ OpenAI   │◄──────────►│Anthropic│         │          │
│  │  │ Adapter  │  (BAA)     │ Adapter  │         │          │
│  │  │ ⚠️ No PHI│            │ ✅ PHI   │         │          │
│  │  └──────────┘            └──────────┘         │          │
│  └────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Key Differentiators

1. **Policy Engine** - YAML-configurable compliance rules that determine which models are legally usable
2. **Risk Scoring** - Vendor-agnostic quality and safety assessment
3. **Audit Logger** - Tamper-evident, 7-year retention (HIPAA requirement)
4. **HIPAA-Aware Routing** - Automatic PHI detection and provider selection

## 🚀 Quick Start

### Installation

```bash
# Clone and navigate
cd healthcare-ai-gateway

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Edit `.env`:

```bash
# Required: API Keys
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# Required: Security (generate strong secrets)
JWT_SECRET=your-secure-secret-min-32-chars
ENCRYPTION_KEY=your-32-byte-encryption-key

# Optional: Database (defaults to SQLite for dev)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/healthcare_gateway
```

### Running the Server

```bash
# Development
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production (with proper SSL/certificates)
uvicorn src.main:app --host 0.0.0.0 --port 443 --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

## 📡 API Usage

### Generate with Compliance Routing

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -H "X-User-ID: user_123" \
  -d '{
    "prompt": "Summarize this medical research article...",
    "industry": "healthcare",
    "data_classification": "phi",
    "system_prompt": "You are a medical research assistant."
  }'
```

### Response

```json
{
  "request_id": "req_abc123",
  "content": "The research indicates...",
  "provider": "anthropic",
  "model": "claude-3-opus-20240229",
  "tokens": {
    "input": 150,
    "output": 300,
    "total": 450
  },
  "latency_ms": 1200,
  "cost_usd": 0.02475,
  "compliance_status": "approved",
  "requires_human_review": true,
  "applied_policies": [
    "phi_requires_hipaa_provider",
    "healthcare_industry_restrictions"
  ],
  "risk_scores": {
    "overall": 0.25,
    "hallucination": 0.15,
    "compliance": 0.10,
    "data_leakage": 0.05,
    "cultural": 0.02
  },
  "risk_flags": ["REQUIRES_HUMAN_REVIEW"]
}
```

### Check Compliance Status

```bash
curl http://localhost:8000/compliance/report
```

## 📋 Policy Configuration

Policies are defined in `config/policies.yaml`:

```yaml
rules:
  - name: custom_healthcare_rule
    description: Custom rule for specific healthcare workflow
    priority: 95
    conditions:
      industry: healthcare
      data_classification: phi
    actions:
      allowed_providers: ["anthropic"]
      require_human_review: true
      allowed_models:
        - "claude-3-opus-20240229"
```

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## 🔒 HIPAA Compliance Notes

This prototype implements key HIPAA requirements:

- ✅ **Access Control** - Authentication required
- ✅ **Audit Controls** - Immutable, tamper-evident logs
- ✅ **Integrity** - Hash-chained audit records
- ✅ **Transmission Security** - HTTPS/SSL (configure in production)
- ⚠️ **Encryption at Rest** - Configure for production database
- ⚠️ **Business Associate Agreement** - Required with Anthropic for PHI

**Important**: This is a prototype. Production deployment requires:
- Full security audit
- BAA with Anthropic (for PHI handling)
- Encryption at rest for all storage
- Proper authentication/authorization system
- Regular compliance assessments

## 📈 Creating Vendor Bidding Dynamics

### Phase 1: Validate (Now)
- Deploy with 3 healthcare design partners
- Demonstrate compliance value
- Collect benchmarking data

### Phase 2: Benchmark (Month 2-3)
- Generate vendor comparison reports
- Publish "AI Safety Scorecard"
- Build enterprise demand

### Phase 3: Leverage (Month 4-6)
- Enterprises start requiring "YourCompany Certified" in RFPs
- Vendors optimize for your compliance schema
- Preferred API access negotiations begin

## 🗺️ Roadmap

### v0.1 (Current) - MVP
- ✅ OpenAI + Anthropic adapters
- ✅ Policy engine with YAML rules
- ✅ Risk scoring module
- ✅ Audit logging
- ⬜ MCP tool integration
- ⬜ Human-in-the-loop workflow

### v0.2 - Enterprise Features
- Web dashboard for compliance monitoring
- Advanced policy editor
- Integration with Epic/Cerner (HL7 FHIR)
- Real-time risk alerting

### v0.3 - Ecosystem
- Open-source core (build community)
- Vendor marketplace
- Compliance certification program

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

This is a strategic prototype. For production use, contact the maintainers.

---

**Built to demonstrate: The future of AI isn't model performance—it's compliance certification.**