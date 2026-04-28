# 最终项目总结

## 1. 项目概览

ServiceOps Agent 是一个面向 AI 平台和企业技术支持场景的智能工单与知识运维 Agent 平台。项目集成 FastAPI 工单系统、SQLAlchemy 数据模型、Agent Workflow、RAG、Tool Calling、Human-in-the-loop 审批、Router LoRA、Verifier LoRA、评测脚本、前端 console 和本地 runtime 脚本。

它不是简单客服机器人，而是围绕企业工单生命周期设计的工程化 LLM 系统：从用户提交问题开始，系统会完成分类、路由、检索证据、调用工具、规划方案、生成草稿、风险校验、人工审批和知识库更新建议。

## 2. 解决的问题

项目针对企业支持团队的典型痛点：

- 重复工单多，人工分诊和路由慢。
- 知识库、错误码文档、SOP 和历史工单分散。
- 客户回复容易缺少证据，风格和质量不稳定。
- LLM 容易生成流畅但不可靠的过度承诺。
- 账号、订单、额度、退款、隐私和事故场景需要审批。
- 需要记录 Agent 每一步的证据、工具调用、审批原因、延迟和失败类型。

## 3. 系统架构

系统采用分层架构：

```text
Frontend Console / API
   ↓
FastAPI Ticket System
   ↓
Agent Workflow
   ├── Router
   ├── RAG Retriever
   ├── Tool Caller
   ├── Planner
   ├── Writer
   ├── Verifier
   └── Human Approval
   ↓
Database / Trace / Reports
```

后端通过 SQLAlchemy 持久化 tickets、ticket_events、tool_calls、retrieved_chunks、approval_requests 和 knowledge_updates。评测层覆盖 Router、Verifier、RAG、End-to-End、manual holdout 和 failure analysis。

## 4. 核心模块

- Ticket System：工单创建、查询、运行 Agent、查看 trace。
- Database Models：保存工单、事件、检索证据、工具调用、审批请求和知识更新建议。
- RAG：BM25、hash-vector fallback、hybrid retrieval、可选 Embedding/Reranker、citation checker。
- Agent Workflow：覆盖分类、缺失信息、检索、工具、规划、草稿、校验、审批和知识更新。
- Tool Calling：执行 mock backend tools，并记录 arguments、results、latency 和 failures。
- Human Approval：高风险动作进入人工审批。
- Router LoRA：学习分类、路由、缺失信息、工具选择和人工审批判断。
- Verifier LoRA：学习证据支持、unsupported claim、citation error、风险和审批判断。
- Evaluation：独立评测模块效果和完整工单生命周期效果。
- Local Runtime：baseline demo 与 LoRA demo 分离，避免混淆可运行状态。

## 5. 数据构造

项目包含：

- 15 intent taxonomy，覆盖 API、账单、RAG、部署、安全、权限、账号、事故和模糊信息等场景。
- 1200 条中文 synthetic enterprise tickets。
- Router SFT train/val/test。
- Verifier SFT train/val/test。
- hard eval sets。
- manual holdout sets：50 Router、50 Verifier、30 E2E。

限制说明：synthetic tickets 是构造数据，manual holdout 是人工整理数据，不是生产客户数据。

## 6. 微调设计

- Base model：`Qwen/Qwen2.5-3B-Instruct`
- 方法：QLoRA
- Router adapter：`outputs/router-lora-v1`
- Verifier adapter：`outputs/verifier-lora-v1`

设计原则：

- 不把企业知识微调进模型，因为知识变化快。
- 用 RAG 管理知识、证据和引用。
- 用 Router/Verifier LoRA 学习稳定决策能力。
- Writer 不优先微调，避免提升流畅表达的同时增加 unsupported claims。
- Router 和 Verifier 是两个独立 adapters，便于分别评测和替换。

## 7. Router LoRA 实验结果

| 指标 | baseline | Router LoRA |
| --- | ---: | ---: |
| json valid rate | 1.0 | 1.0 |
| intent accuracy | 0.625 | 0.8917 |
| routing accuracy | 0.7167 | 0.9917 |
| priority accuracy | 0.85 | 0.9583 |
| missing-info F1 | 0.8 | 0.7639 |
| required-tools accuracy | 0.725 | 0.8167 |
| requires-human accuracy | 0.85 | 0.9333 |
| final eval_loss | n/a | 0.2099 |

Router LoRA 的价值在于让工单入口更稳定：分类更准、路由更准、工具选择更接近目标，高风险工单更容易进入审批路径。

## 8. Verifier LoRA 实验结果

| 指标 | prompt baseline | Verifier LoRA |
| --- | ---: | ---: |
| json valid rate | 1.0 | 1.0 |
| support accuracy | 0.41 | 0.99 |
| unsupported claim recall | 0.7783 | 0.97 |
| citation error detection | 1.0 | 0.96 |
| risk recall | 0.9091 | 0.987 |
| requires approval accuracy | 0.61 | 0.99 |
| false approval rate | 0.07 | 0.0 |
| final eval_loss | n/a | 0.2007 |

Verifier LoRA 的关键价值是降低 false approval rate。企业 Agent 中，“不该放行的回复被放行”比“回复不够漂亮”更危险。

## 9. RAG 评测结果

| variant | top-k hit | citation hit | 状态 |
| --- | ---: | ---: | --- |
| BM25 only | 0.50 | 0.50 | ok |
| Hash-vector only | 0.72 | 0.72 | ok |
| Hybrid | 0.72 | 0.72 | ok |
| Real embedding only | n/a | n/a | optional dependency unavailable |
| Hybrid + reranker | n/a | n/a | optional dependency unavailable |

hard RAG eval top-k hit 和 citation hit 均为 `0.72`。这说明当前 RAG 能命中相当一部分证据，但 citation miss 仍是端到端成功率的重要瓶颈。

## 10. End-to-End 评测结果

End-to-End eval 衡量完整工单生命周期，而不是单个模块：

| dataset | mode | success | tool recall | citation hit | unsupported claim rate |
| --- | --- | ---: | ---: | ---: | ---: |
| synthetic hard | direct_llm | 0.0 | 0.0 | 0.0 | 1.0 |
| synthetic hard | rag_only | 0.0 | 0.0 | 0.7 | 0.0 |
| synthetic hard | agent_rule_router_prompt_verifier | 0.4667 | 1.0 | 0.7667 | 0.0 |
| manual holdout | direct_llm | 0.0 | 0.0 | 0.0 | 1.0 |
| manual holdout | rag_only | 0.0 | 0.0 | 0.6 | 0.0 |
| manual holdout | agent_rule_router_prompt_verifier | 0.3 | 0.8333 | 0.6333 | 0.0 |

LoRA E2E runtime 已接入，并已在本地 MPS 环境完成小规模验证：`agent_router_lora_verifier_lora` 对 `data/eval/manual_holdout_e2e.jsonl` 跑通 5 条样本。由于 Mac 本地推理较慢，完整 LoRA E2E 仍建议在 GPU 上补跑。项目不把 module-level LoRA 指标冒充完整 E2E 指标。

## 11. Manual Holdout 结果

Manual holdout 用于测试模板外泛化：

- Router manual rule baseline：intent `0.8`，routing `0.86`，priority `0.92`，requires-human `0.92`。
- Verifier manual prompt baseline：support `0.12`，unsupported recall `1.0`，false approval `0.38`。
- E2E manual rule-agent success：`0.3`。

结论：manual cases 暴露了 RAG citation、tool coverage 和 Verifier baseline 的明显瓶颈，也说明需要在可加载 base model 的环境中补跑 LoRA E2E。

## 12. Failure Analysis 总结

主要失败类型：

- classification_error：混合意图或模糊工单导致 Router 混淆。
- routing_error：预测团队和 taxonomy owner 不一致。
- retrieval_miss：RAG 没有命中期望证据，是当前 E2E 成功率的重要瓶颈。
- tool_call_error：工具序列没有覆盖期望查询。
- verifier_false_approval：风险回复被错误放行。
- verifier_over_block：低风险回复被过度拦截。

改进方向：

- 增加 mixed-intent manual examples。
- 加强 metadata filtering、chunk title 和 reranker。
- 增加 tool argument validation 和 fallback 查询。
- 引入真实 Embedding/Reranker 后重跑 RAG ablation。
- 在 GPU/base-model 环境补跑 LoRA E2E。

## 13. 哪些部分接近生产系统

- 状态化工单流程。
- 真实后端函数形式的 Tool Calling。
- 工具调用、RAG evidence、审批请求和事件 trace 的持久化。
- Human-in-the-loop 审批边界。
- Router/Verifier adapters 分离。
- 模块评测、E2E 评测、manual holdout 和 failure analysis。
- 本地 runtime 检查和 demo 脚本。

## 14. 哪些部分仍是模拟/非生产

- 企业数据是 synthetic/mock data。
- 知识库是本地 Markdown 文档。
- 工具没有连接真实订单、计费、账号、部署和安全平台。
- manual holdout 不是生产流量。
- 本地 LoRA demo 已具备 base model 和 adapters，并已通过 smoke/API 验证。
- 生产化还需要权限系统、审计系统、监控告警、灰度发布、线上评测和数据合规流程。

## 15. 最终状态

- project_version: v1.0-ready
- router_lora_trained: true
- verifier_lora_trained: true
- local_lora_runtime_added: true
- local_base_model_present: true
- local_lora_smoke_test_completed: true
- local_lora_small_e2e_completed: true
- repository_ready: true
