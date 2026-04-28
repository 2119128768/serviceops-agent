# End-to-End Eval

Dataset: `data/eval/manual_holdout_e2e.jsonl`

Sample count: `5`

| mode | sample_count | intent | routing | priority | tool_recall | citation | human | unsupported | success | latency_ms | tool_calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| agent_router_lora_verifier_lora | 5 | 0.6 | 0.8 | 1.0 | 0.7333 | 0.8 | 0.8 | 0.0 | 0.0 | 21620.734 | 2.8 |

Target comparison modes:

- direct_llm
- rag_only
- agent_rule_router_prompt_verifier
- agent_router_lora_prompt_verifier
- agent_router_lora_verifier_lora
