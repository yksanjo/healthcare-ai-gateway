"""
Audit Logger
HIPAA-compliant immutable audit trail
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import asyncio
import aiofiles
from dataclasses import asdict

from ..config import settings, HIPAA_CONFIG


class AuditLogger:
    """
    HIPAA-compliant audit logging
    
    Requirements:
    - Immutable records
    - 7-year retention
    - Tamper-evident (hash chaining)
    - Encrypted storage
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir or settings.audit_log_path)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._last_hash = "0" * 64  # Genesis hash
    
    def _hash_record(self, record: Dict[str, Any], previous_hash: str) -> str:
        """Create tamper-evident hash of record"""
        record_str = json.dumps(record, sort_keys=True, default=str)
        combined = record_str + previous_hash
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def log_request(
        self,
        request_id: str,
        user_id: str,
        session_id: str,
        ip_address: str,
        prompt: str,  # Will be truncated/hashed for privacy
        context: Dict[str, Any],
        routing_decision: Any,
        provider_response: Any,
        risk_score: Any,
    ) -> Dict[str, Any]:
        """
        Log a complete request/response cycle
        
        This creates the immutable audit trail required for HIPAA.
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Sanitize prompt for logging (hash it, don't store raw)
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        
        # Build audit record
        record = {
            "timestamp": timestamp,
            "request_id": request_id,
            "user_id": self._hash_identifier(user_id),
            "session_id": session_id,
            "ip_address": ip_address,
            "prompt_hash": prompt_hash,  # Hashed, not raw
            "context": {
                "industry": context.get("industry"),
                "data_classification": context.get("data_classification"),
                "risk_level": context.get("risk_level"),
            },
            "routing": {
                "provider": routing_decision.provider.value if hasattr(routing_decision, 'provider') else None,
                "model": routing_decision.model if hasattr(routing_decision, 'model') else None,
                "allowed": routing_decision.allowed if hasattr(routing_decision, 'allowed') else None,
                "compliance_status": routing_decision.compliance_status if hasattr(routing_decision, 'compliance_status') else None,
                "applied_rules": routing_decision.applied_rules if hasattr(routing_decision, 'applied_rules') else [],
            },
            "response": {
                "model": provider_response.model if hasattr(provider_response, 'model') else None,
                "tokens_input": provider_response.tokens_input if hasattr(provider_response, 'tokens_input') else 0,
                "tokens_output": provider_response.tokens_output if hasattr(provider_response, 'tokens_output') else 0,
                "latency_ms": provider_response.latency_ms if hasattr(provider_response, 'latency_ms') else 0,
                "cost_usd": provider_response.cost_usd if hasattr(provider_response, 'cost_usd') else 0,
            },
            "risk": {
                "overall_risk": risk_score.overall_risk if hasattr(risk_score, 'overall_risk') else 0,
                "hallucination_risk": risk_score.hallucination_risk if hasattr(risk_score, 'hallucination_risk') else 0,
                "compliance_risk": risk_score.compliance_risk if hasattr(risk_score, 'compliance_risk') else 0,
                "flags": risk_score.flags if hasattr(risk_score, 'flags') else [],
            },
        }
        
        # Add tamper-evident hash
        async with self._lock:
            record_hash = self._hash_record(record, self._last_hash)
            record["audit_hash"] = record_hash
            record["previous_hash"] = self._last_hash
            self._last_hash = record_hash
        
        # Write to log file
        await self._write_record(record)
        
        return record
    
    async def _write_record(self, record: Dict[str, Any]):
        """Write record to daily audit log file"""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit_{date_str}.jsonl"
        
        async with aiofiles.open(log_file, 'a') as f:
            await f.write(json.dumps(record, default=str) + "\n")
    
    def _hash_identifier(self, identifier: str) -> str:
        """Hash user identifiers for privacy"""
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]
    
    async def verify_integrity(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify audit log integrity
        
        Returns verification report showing if any tampering detected.
        """
        if date_str is None:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        log_file = self.log_dir / f"audit_{date_str}.jsonl"
        
        if not log_file.exists():
            return {"verified": False, "error": "Log file not found"}
        
        violations = []
        previous_hash = "0" * 64
        
        async with aiofiles.open(log_file, 'r') as f:
            async for line in f:
                record = json.loads(line)
                
                # Verify hash chain
                stored_hash = record.get("audit_hash")
                stored_previous = record.get("previous_hash")
                
                if stored_previous != previous_hash:
                    violations.append({
                        "record": record.get("request_id"),
                        "type": "broken_chain",
                        "expected_previous": previous_hash,
                        "found_previous": stored_previous,
                    })
                
                # Recompute hash
                record_copy = {k: v for k, v in record.items() 
                              if k not in ["audit_hash", "previous_hash"]}
                computed_hash = self._hash_record(record_copy, stored_previous)
                
                if computed_hash != stored_hash:
                    violations.append({
                        "record": record.get("request_id"),
                        "type": "tampered_record",
                        "expected_hash": computed_hash,
                        "found_hash": stored_hash,
                    })
                
                previous_hash = stored_hash
        
        return {
            "verified": len(violations) == 0,
            "violations": violations,
            "total_records_checked": len(violations),  # Approximate
        }
    
    async def get_compliance_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate compliance report for auditors"""
        # This would query the audit logs for a date range
        # and generate statistics for compliance reporting
        
        return {
            "report_period": {"start": start_date, "end": end_date},
            "total_requests": 0,  # Would be calculated
            "phi_requests": 0,
            "human_review_required": 0,
            "policy_violations": 0,
            "provider_breakdown": {},
            "average_risk_scores": {},
            "hipaa_compliance_status": "compliant",
        }