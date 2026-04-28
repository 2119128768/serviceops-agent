# Local LoRA E2E Small Eval

- dataset: `data/eval/manual_holdout_e2e.jsonl`
- limit: `5`
- output: `reports/local_lora_e2e_small_results.jsonl`

```json
{
  "intent_accuracy": 0.6,
  "routing_accuracy": 0.8,
  "priority_accuracy": 1.0,
  "required_tool_recall": 0.7333,
  "citation_hit_rate": 0.8,
  "requires_human_accuracy": 0.8,
  "unsupported_claim_rate": 0.0,
  "end_to_end_success_rate": 0.0,
  "avg_latency_ms": 21620.734,
  "avg_tool_calls": 2.8,
  "mode": "agent_router_lora_verifier_lora",
  "rows": 5,
  "dataset": "data/eval/manual_holdout_e2e.jsonl",
  "sample_count": 5
}
```
