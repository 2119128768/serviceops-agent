# E2E LoRA Integration

## Runtime Design

- `agent_router_lora_prompt_verifier` uses `LoraRouterModel` with the Router adapter and the baseline verifier.
- `agent_router_lora_verifier_lora` uses `LoraRouterModel` and `LoraVerifierModel`.
- The shared `LoraJsonModel` loads the base model and PEFT adapter once per evaluator instance.
- Generation is deterministic with `do_sample=False`, `attention_mask`, and `max_new_tokens <= 256`.
- If the local machine cannot load the base model, LoRA E2E modes are marked unavailable rather than replaced with proxy metrics.

## Configuration

- base_model: `Qwen/Qwen2.5-3B-Instruct`
- router_adapter: `outputs/router-lora-v1`
- verifier_adapter: `outputs/verifier-lora-v1`

## Mode Status

| mode | status | sample_count | success | routing | unsupported |
| --- | --- | ---: | ---: | ---: | ---: |
| direct_llm | ok | 30 | 0.0 | 0.9 | 1.0 |
| rag_only | ok | 30 | 0.0 | 0.9 | 0.0 |
| agent_rule_router_prompt_verifier | ok | 30 | 0.3 | 0.9 | 0.0 |
| agent_router_lora_prompt_verifier | unavailable: Install LoRA runtime dependencies with: pip install -e '.[training]' | 30 | n/a | n/a | n/a |
| agent_router_lora_verifier_lora | unavailable: Install LoRA runtime dependencies with: pip install -e '.[training]' | 30 | n/a | n/a | n/a |
