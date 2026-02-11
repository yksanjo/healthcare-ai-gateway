#!/usr/bin/env python3
"""
Healthcare AI Gateway - Demo Script
Demonstrates the core value proposition: compliance-aware routing
"""

import asyncio
import json
from src.policy import PolicyEngine, DataClassification, Industry
from src.risk import RiskEngine
from src.providers import ProviderFactory, ProviderRequest, ProviderType


async def demo_policy_engine():
    """Demonstrate the policy-based routing"""
    print("\n" + "="*70)
    print("🏥 HEALTHCARE AI GATEWAY - POLICY ENGINE DEMO")
    print("="*70)
    
    engine = PolicyEngine()
    
    test_cases = [
        {
            "name": "PHI Data (Medical Record)",
            "context": {
                "industry": Industry.HEALTHCARE.value,
                "data_classification": DataClassification.PHI.value,
                "risk_level": 0.8,
            },
            "expected": "anthropic (BAA required)",
        },
        {
            "name": "Public Health Information",
            "context": {
                "industry": Industry.HEALTHCARE.value,
                "data_classification": DataClassification.PUBLIC.value,
                "risk_level": 0.1,
            },
            "expected": "any (cost optimized)",
        },
        {
            "name": "Financial Services Data",
            "context": {
                "industry": Industry.FINANCE.value,
                "data_classification": DataClassification.CONFIDENTIAL.value,
                "risk_level": 0.6,
            },
            "expected": "anthropic (conservative)",
        },
        {
            "name": "General Admin Task",
            "context": {
                "industry": Industry.GENERAL.value,
                "data_classification": DataClassification.INTERNAL.value,
                "risk_level": 0.2,
            },
            "expected": "any (default)",
        },
    ]
    
    for test in test_cases:
        print(f"\n📋 Test: {test['name']}")
        print(f"   Context: {json.dumps(test['context'], indent=6)}")
        
        decision = engine.evaluate(test['context'])
        
        print(f"   ✅ Decision:")
        print(f"      Provider: {decision.provider.value}")
        print(f"      Model: {decision.model}")
        print(f"      Allowed: {decision.allowed}")
        print(f"      Human Review: {decision.requires_human_review}")
        print(f"      Policies Applied: {', '.join(decision.applied_rules)}")
        print(f"      Expected: {test['expected']}")
        
        if decision.provider.value in test['expected'] or 'any' in test['expected']:
            print(f"   ✓ PASS")
        else:
            print(f"   ⚠ Check logic")


async def demo_risk_scoring():
    """Demonstrate risk scoring"""
    print("\n" + "="*70)
    print("🔍 RISK SCORING ENGINE DEMO")
    print("="*70)
    
    engine = RiskEngine()
    
    test_outputs = [
        {
            "name": "Safe General Output",
            "text": "The patient appointment has been scheduled for tomorrow at 2 PM.",
            "context": {"industry": "healthcare", "data_classification": "internal"},
        },
        {
            "name": "High-Risk Medical Advice",
            "text": "You should definitely stop taking your current medication and start this new treatment immediately. It will cure your condition.",
            "context": {"industry": "healthcare", "data_classification": "phi"},
        },
        {
            "name": "Uncertain Diagnosis",
            "text": "I think maybe this could be a sign of something serious, but I'm not really sure. It might be nothing.",
            "context": {"industry": "healthcare", "data_classification": "phi"},
        },
        {
            "name": "Potential PHI Leak",
            "text": "Patient John Smith, SSN 123-45-6789, DOB 01/15/1980, email john.smith@email.com has been diagnosed with...",
            "context": {"industry": "healthcare", "data_classification": "phi"},
        },
    ]
    
    for test in test_outputs:
        print(f"\n📝 Test: {test['name']}")
        print(f"   Text: {test['text'][:60]}...")
        
        score = engine.analyze(test['text'], test['context'])
        
        print(f"   📊 Risk Scores:")
        print(f"      Overall: {score.overall_risk:.2f}")
        print(f"      Hallucination: {score.hallucination_risk:.2f}")
        print(f"      Compliance: {score.compliance_risk:.2f}")
        print(f"      Data Leakage: {score.data_leakage_risk:.2f}")
        
        if score.flags:
            print(f"   🚩 Flags: {', '.join(score.flags)}")
        if score.recommendations:
            print(f"   💡 Recommendations: {', '.join(score.recommendations)}")


async def demo_provider_comparison():
    """Demonstrate how the gateway creates vendor comparison"""
    print("\n" + "="*70)
    print("📊 PROVIDER BENCHMARKING (The 'Force Bidding' Mechanism)")
    print("="*70)
    
    print("""
This demonstrates how the gateway creates comparative data that
forces vendors to compete for preferred placement.

When enterprises see:
┌──────────────────────────────────────────────────────────────┐
│  Vendor   │ Compliance │ Risk Score │ Latency │ Cost/1K    │
├──────────────────────────────────────────────────────────────┤
│ Anthropic │    98%     │    0.12    │  850ms  │   $0.045   │
│ OpenAI    │    45%     │    0.28    │  720ms  │   $0.020   │
└──────────────────────────────────────────────────────────────┘

Vendors must optimize for YOUR scoring to win enterprise deals.
This is the leverage point.
    """)
    
    # Simulate benchmark data
    risk_engine = RiskEngine()
    
    # Sample outputs from both providers for same prompts
    samples = [
        {
            "output": "Based on the clinical guidelines, patients with this condition typically require monitoring.",
            "context": {"industry": "healthcare", "data_classification": "phi"},
        },
        {
            "output": "The research indicates a 15% improvement in outcomes with this treatment protocol.",
            "context": {"industry": "healthcare", "data_classification": "confidential"},
        },
    ]
    
    providers = ["anthropic", "openai"]
    
    print("\n🔄 Simulated Benchmark Results:")
    for provider in providers:
        result = risk_engine.benchmark_provider(provider, samples)
        print(f"\n   {provider.upper()}:")
        print(f"      Avg Hallucination Risk: {result['avg_hallucination_risk']:.3f}")
        print(f"      Avg Compliance Risk: {result['avg_compliance_risk']:.3f}")
        print(f"      Compliance Score: {result['compliance_score']:.1%}")


async def demo_compliance_rules():
    """Show the compliance rule engine"""
    print("\n" + "="*70)
    print("⚖️  COMPLIANCE RULES ENGINE")
    print("="*70)
    
    engine = PolicyEngine()
    report = engine.get_compliance_report()
    
    print(f"\n📋 Configuration:")
    print(f"   Total Rules: {report['total_rules']}")
    print(f"   Enabled Rules: {report['enabled_rules']}")
    
    print(f"\n🔒 Provider HIPAA Status:")
    for provider, status in report['provider_status'].items():
        print(f"   {provider.upper()}:")
        print(f"      BAA Available: {'✅' if status['baa_available'] else '❌'}")
        print(f"      HIPAA Compliant: {'✅' if status['hipaa_compliant'] else '❌'}")
        print(f"      PHI Allowed: {'✅' if status['allowed_for_phi'] else '❌'}")
    
    print(f"\n💾 HIPAA Requirements:")
    print(f"   Audit Retention: 7 years (2555 days)")
    print(f"   Encryption: Required for PHI/Restricted")
    print(f"   Immutable Logs: ✅ Tamper-evident hashes")


async def main():
    """Run all demos"""
    print("\n" + "🚀" * 35)
    print("   HEALTHCARE AI GATEWAY - STRATEGIC PROTOTYPE DEMO")
    print("   Proving compliance creates vendor leverage")
    print("🚀" * 35)
    
    await demo_policy_engine()
    await demo_risk_scoring()
    await demo_provider_comparison()
    await demo_compliance_rules()
    
    print("\n" + "="*70)
    print("✅ DEMO COMPLETE")
    print("="*70)
    print("""
Next Steps:
1. Set API keys in .env
2. Run: uvicorn src.main:app --reload
3. Test: curl -X POST http://localhost:8000/generate ...
4. Find 3 healthcare design partners
5. Generate vendor scorecards to create bidding dynamics
    """)


if __name__ == "__main__":
    asyncio.run(main())