# Failure Analysis

| failure_type | count |
| --- | ---: |
| classification_error | 2 |
| routing_error | 1 |
| missing_info_error | 0 |
| required_tool_error | 0 |
| retrieval_miss | 1 |
| wrong_citation | 0 |
| tool_call_error | 4 |
| verifier_false_approval | 1 |
| verifier_over_block | 0 |
| unsupported_claim | 0 |
| refusal_needed_but_not_refused | 0 |
| latency_high | 5 |
| json_invalid | 0 |

## Samples

### classification_error
- ticket_id=MH_E2E_001 mode=agent_router_lora_verifier_lora expected=api_quota_error predicted=api_latency root_cause=Router confused mixed or underspecified enterprise support intent. fix=Add manual mixed-intent examples and route ambiguous cases to follow-up. ticket=客户说模型接口又慢又偶尔 429，昨天刚充值，只有 request_id: req_manual_001。
- ticket_id=MH_E2E_002 mode=agent_router_lora_verifier_lora expected=api_quota_error predicted=quota_billing root_cause=Router confused mixed or underspecified enterprise support intent. fix=Add manual mixed-intent examples and route ambiguous cases to follow-up. ticket=报错 quota exceeded，但财务说订单已经付了，订单号 ord_manual_002，账号没找到。

### tool_call_error
- ticket_id=MH_E2E_001 mode=agent_router_lora_verifier_lora expected=api_quota_error predicted=api_latency root_cause=Tool sequence did not cover expected backend lookup. fix=Add tool argument validation and retry/fallback logic. ticket=客户说模型接口又慢又偶尔 429，昨天刚充值，只有 request_id: req_manual_001。
- ticket_id=MH_E2E_002 mode=agent_router_lora_verifier_lora expected=api_quota_error predicted=quota_billing root_cause=Tool sequence did not cover expected backend lookup. fix=Add tool argument validation and retry/fallback logic. ticket=报错 quota exceeded，但财务说订单已经付了，订单号 ord_manual_002，账号没找到。
- ticket_id=MH_E2E_003 mode=agent_router_lora_verifier_lora expected=api_rate_limit_error predicted=api_rate_limit_error root_cause=Tool sequence did not cover expected backend lookup. fix=Add tool argument validation and retry/fallback logic. ticket=线上突然大量 429，像余额不足，也可能是并发打满，acc_manual_003。
- ticket_id=MH_E2E_004 mode=agent_router_lora_verifier_lora expected=api_rate_limit_error predicted=api_rate_limit_error root_cause=Tool sequence did not cover expected backend lookup. fix=Add tool argument validation and retry/fallback logic. ticket=QPS 一到 50 就失败，控制台提示 rate limited，request_id 是 req_manual_004。

### verifier_false_approval
- ticket_id=MH_E2E_001 mode=agent_router_lora_verifier_lora expected=api_quota_error predicted=api_latency root_cause=Verifier allowed a case that should require human approval. fix=Increase negative verifier examples for sensitive actions. ticket=客户说模型接口又慢又偶尔 429，昨天刚充值，只有 request_id: req_manual_001。

### latency_high
- ticket_id=MH_E2E_001 mode=agent_router_lora_verifier_lora expected=api_quota_error predicted=api_latency root_cause=Evaluation exceeded latency threshold. fix=Cache retrievers/models and limit generated tokens. ticket=客户说模型接口又慢又偶尔 429，昨天刚充值，只有 request_id: req_manual_001。
- ticket_id=MH_E2E_002 mode=agent_router_lora_verifier_lora expected=api_quota_error predicted=quota_billing root_cause=Evaluation exceeded latency threshold. fix=Cache retrievers/models and limit generated tokens. ticket=报错 quota exceeded，但财务说订单已经付了，订单号 ord_manual_002，账号没找到。
- ticket_id=MH_E2E_003 mode=agent_router_lora_verifier_lora expected=api_rate_limit_error predicted=api_rate_limit_error root_cause=Evaluation exceeded latency threshold. fix=Cache retrievers/models and limit generated tokens. ticket=线上突然大量 429，像余额不足，也可能是并发打满，acc_manual_003。
- ticket_id=MH_E2E_004 mode=agent_router_lora_verifier_lora expected=api_rate_limit_error predicted=api_rate_limit_error root_cause=Evaluation exceeded latency threshold. fix=Cache retrievers/models and limit generated tokens. ticket=QPS 一到 50 就失败，控制台提示 rate limited，request_id 是 req_manual_004。
- ticket_id=MH_E2E_005 mode=agent_router_lora_verifier_lora expected=api_auth_error predicted=api_auth_error root_cause=Evaluation exceeded latency threshold. fix=Cache retrievers/models and limit generated tokens. ticket=API key 明明没改，今天开始 401，proj_manual_005。

### routing_error
- ticket_id=MH_E2E_002 mode=agent_router_lora_verifier_lora expected=api_quota_error predicted=quota_billing root_cause=Predicted team did not match taxonomy owner for the expected intent. fix=Tighten taxonomy labels and add team-level contrastive examples. ticket=报错 quota exceeded，但财务说订单已经付了，订单号 ord_manual_002，账号没找到。

### retrieval_miss
- ticket_id=MH_E2E_005 mode=agent_router_lora_verifier_lora expected=api_auth_error predicted=api_auth_error root_cause=RAG retrieval missed expected evidence document. fix=Improve metadata filters, chunk titles, and reranker coverage. ticket=API key 明明没改，今天开始 401，proj_manual_005。
