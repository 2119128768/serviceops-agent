# Local LoRA Smoke Test

```json
{
  "router": {
    "intent": "api_quota_error",
    "missing_info": [
      "account_id"
    ],
    "needs_rag": true,
    "priority": "P2",
    "product": "model_api",
    "raw_json_valid": true,
    "required_tools": [
      "check_api_status",
      "query_order_status",
      "get_sla_policy"
    ],
    "requires_human": true,
    "risk_level": "medium",
    "secondary_team": "billing_system",
    "suggested_team": "platform_support"
  },
  "runtime": {
    "device": "mps",
    "last_generation_ms": 4061.976,
    "load_seconds": 40.914,
    "multi_adapter": true
  },
  "verifier": {
    "citation_errors": [],
    "contains_sensitive_action": false,
    "decision": "revise_before_reply",
    "raw_json_valid": true,
    "requires_approval": true,
    "risk_level": "high",
    "supported_by_evidence": false,
    "unsupported_claims": []
  }
}
```
