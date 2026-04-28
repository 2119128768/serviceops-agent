# ServiceOps Agent 中文架构报告

## 1. 项目定位

ServiceOps Agent 是一个面向企业技术支持场景的智能工单与知识运维 Agent 平台。它的定位不是客服话术生成器，而是一个可运行、可追踪、可评测的企业工单处理系统。

系统将 LLM 能力放在工程流程中使用：Router 做结构化分诊，RAG 提供可引用证据，Tool Calling 查询业务状态，Planner 生成处理步骤，Writer 生成回复草稿，Verifier 做证据与风险校验，Human-in-the-loop 负责高风险动作审批。

核心展示能力：

- AI Backend：FastAPI、SQLAlchemy、状态机、trace 和前端 console。
- Agent Workflow：多节点工单处理链路，而不是单轮 prompt。
- RAG：企业知识库、历史工单、citation checker 和 retrieval eval。
- LoRA/QLoRA：Router 与 Verifier 两个独立 adapters。
- LLMOps：评测脚本、failure analysis 和本地 runtime。

## 2. 业务背景

企业 AI 平台的技术支持工单经常具备以下特点：

- 问题跨系统：API、账号、订单、额度、部署、知识库、安全和 SLA 常常混在一起。
- 信息不完整：客户可能只给 `request_id`，没有 `account_id` 或 `order_id`。
- 知识变化快：错误码、额度策略、RAG 导入规则和部署建议会持续更新。
- 风险边界强：账号、订单、额度、退款、隐私和关闭工单等动作不能让模型自动决定。
- 质量需要量化：团队需要知道分类准不准、引用准不准、工具有没有调用、是否过度承诺。

因此，一个真正有企业味道的 Agent 需要同时处理流程、证据、工具、审批和评测。

## 3. 系统边界

当前系统是工程化模拟项目，边界必须说清楚：

- 工单数据是 synthetic tickets 和 manual holdout，不是生产客户数据。
- 企业知识库是本地 Markdown 文档，不是公司内部真实知识库。
- 业务工具连接 mock database，不连接真实订单、计费、账号、部署或安全系统。
- Router LoRA 和 Verifier LoRA 已训练完成，但 adapters 不包含完整模型，运行时依赖 `Qwen/Qwen2.5-3B-Instruct` base model。
- 本地 baseline demo 可以运行；本地 LoRA demo 需要 base model。当前本机已经下载 `models/Qwen2.5-3B-Instruct` 并完成 smoke/API 验证。

这个边界不削弱项目价值，反而体现了工程诚实性：项目展示的是系统设计、训练评测和安全控制能力，不虚构生产数据或生产接入。

## 4. 总体架构图

```text
用户提交工单
   ↓
Frontend Console / FastAPI API
   ↓
Ticket System
   ├── tickets
   ├── ticket_events
   ├── tool_calls
   ├── retrieved_chunks
   ├── approval_requests
   └── knowledge_updates
   ↓
Agent Workflow
   ├── classify_ticket
   │     └── Router / Router LoRA
   ├── check_missing_info
   ├── retrieve_knowledge
   │     └── RAG Retriever
   ├── retrieve_similar_tickets
   ├── call_tools
   │     └── ToolRegistry
   ├── plan_solution
   ├── draft_reply
   ├── verify_response
   │     └── Verifier / Verifier LoRA
   ├── request_approval
   └── update_knowledge
   ↓
输出结果
   ├── 分类 / 优先级 / 路由
   ├── 缺失信息追问
   ├── RAG evidence
   ├── Tool results
   ├── 处理方案
   ├── 回复草稿
   ├── Verifier decision
   ├── Human Approval request
   └── Knowledge update proposal
   ↓
Eval & Reports
```

## 5. 请求生命周期

下面用一条示例工单串起完整流程：

```text
模型 API 返回 429，但昨天已经充值了，request_id=req_001，为什么还是不能调用？
```

### 5.1 Router output

Router 首先将自然语言工单转成结构化 JSON。以下是示例化输出，用来说明字段含义：

```json
{
  "intent": "api_quota_error",
  "product": "model_api",
  "priority": "P2",
  "suggested_team": "platform_support",
  "secondary_team": "billing_system",
  "missing_info": ["account_id", "order_id"],
  "required_tools": ["check_api_status", "query_order_status", "get_sla_policy"],
  "needs_rag": true,
  "requires_human": true,
  "risk_level": "medium"
}
```

这个结果决定后续处理路径：需要查 API 请求、查订单或额度同步、检索错误码和充值同步文档，并且因为涉及订单和额度，需要人工审批。

### 5.2 RAG evidence

RAG Retriever 会根据工单文本和 intent 检索企业知识库。可能命中的 evidence 包括：

| evidence | 作用 |
| --- | --- |
| `api/error_codes.md` | 解释 `429`、`quota_exceeded`、`rate_limited` 的区别 |
| `billing/recharge_sync.md` | 解释充值后额度同步状态和延迟 |
| `billing/quota_policy.md` | 解释套餐额度、QPS 限制和额度不足 |
| `sop/escalation_policy.md` | 说明何时升级计费系统组或平台支持组 |

RAG 输出不是最终答案，而是带 `doc_id`、`chunk_id`、`title`、`source_path` 和 `score` 的证据列表。

### 5.3 tool calls

Tool Caller 会优先使用工单里的 `request_id`：

```json
[
  {
    "tool_name": "check_api_status",
    "arguments": {"request_id": "req_001"}
  },
  {
    "tool_name": "get_sla_policy",
    "arguments": {"priority": "P2"}
  }
]
```

如果 `check_api_status` 返回了 `account_id`，系统会继续查询：

```json
[
  {
    "tool_name": "get_customer_profile",
    "arguments": {"account_id": "acc_001"}
  },
  {
    "tool_name": "query_order_status",
    "arguments": {"account_id": "acc_001"}
  }
]
```

这些工具调用来自 mock database，目的是模拟企业系统集成，而不是声称已连接真实生产系统。

### 5.4 plan

Planner 根据 evidence 和 tool results 生成处理步骤：

```text
1. 根据 request_id 查询 API 请求日志，区分 quota_exceeded 与 rate_limited。
2. 补齐 account_id 和 order_id 后查询订单支付状态与 quota_sync_status。
3. 如果订单已支付但 quota_sync_status 非 synced，升级 billing_system 处理额度同步。
4. 如果是 QPS 限流，返回当前套餐限制、重试策略和升级建议。
5. 涉及额度恢复、退款、套餐修改或账号信息时进入 Human Approval。
```

### 5.5 draft reply

Writer 只生成 draft reply，不直接作为最终回复：

```text
您好，429 可能由额度不足、QPS 限流或额度同步延迟导致。
我们已根据 request_id=req_001 做初步排查，但还需要补充 account_id 或 order_id，才能确认订单支付状态和 quota_sync_status。
如果确认订单已支付但额度未同步，我们会升级计费系统组处理；涉及额度调整的动作需要人工审批后执行。
引用来源：api/error_codes.md；billing/recharge_sync.md；sop/escalation_policy.md。
```

### 5.6 verifier decision

Verifier 检查 draft reply 是否有依据、是否越权、是否需要审批：

```json
{
  "supported_by_evidence": true,
  "unsupported_claims": [],
  "citation_errors": [],
  "contains_sensitive_action": true,
  "requires_approval": true,
  "risk_level": "medium",
  "decision": "request_human_approval"
}
```

如果 draft reply 写了“订单已支付”但工具结果没有证明，Verifier 应该标记 unsupported claim。如果写了“额度已恢复”或“立即退款”，则应该请求人工审批或要求改写。

### 5.7 human approval status

由于该工单涉及充值、额度和可能的账号信息，最终状态会进入：

```text
WAITING_HUMAN_APPROVAL
```

审批通过后，人工处理人可以确认是否发送回复、升级计费系统组、补充知识库或要求客户提供更多信息。

## 6. 工单状态流

系统的典型状态包括：

- `CREATED`：工单已创建。
- `CLASSIFIED`：Router 完成分类、优先级、路由和缺失信息识别。
- `WAITING_CUSTOMER`：缺失字段阻塞处理，需要客户补充。
- `IN_PROGRESS`：正在检索知识、调用工具或生成方案。
- `WAITING_HUMAN_APPROVAL`：涉及敏感动作或风险动作，需要人工审批。
- `ESCALATED`：P0/P1、incident 或跨团队问题升级。
- `RESOLVED`：证据充分、风险可控且处理完成。

状态流由 Agent Workflow、Verifier decision 和 approval rules 共同决定，不由 Writer 自由生成。

## 7. Agent 节点设计

### classify_ticket

调用 Router baseline 或 Router LoRA，将工单文本转成结构化字段。该节点输出 intent、product、priority、suggested_team、secondary_team、missing_info、required_tools、needs_rag、requires_human 和 risk_level。

### check_missing_info

判断缺失信息是否阻塞后续处理。例如 `api_quota_error` 通常需要 `account_id` 或 `order_id`，`deployment_failure` 通常需要 `deployment_id`。如果阻塞，会生成追问文本。

### retrieve_knowledge

使用 RAG Retriever 从 `data/kb_docs/` 检索相关知识，输出证据 chunks。它为 Planner、Writer 和 Verifier 提供依据。

### retrieve_similar_tickets

检索历史相似工单，帮助系统复用处理经验。当前项目使用本地模拟数据，重点展示接口和链路位置。

### call_tools

根据 identifiers 和 `required_tools` 执行业务工具。当前工具包括 `check_api_status`、`query_order_status`、`get_customer_profile`、`get_deployment_status`、`get_sla_policy`、`route_ticket` 和 `create_approval_request`。

### plan_solution

根据 Router output、RAG evidence 和 tool results 生成排查步骤。这个节点把“如何处理”从 Writer 中拆出来，减少回复草稿自由发挥。

### draft_reply

生成用户回复草稿和内部处理说明。草稿必须使用已有证据和工具结果，不能凭空承诺订单状态、额度恢复或问题已修复。

### verify_response

调用 Verifier baseline 或 Verifier LoRA，检查 support、unsupported claims、citation errors、sensitive actions、requires_approval 和 decision。

### request_approval

当 Router 或 Verifier 判断需要审批时，创建 approval request，将风险原因、动作和 payload 持久化，并更新工单状态。

### update_knowledge

当工单暴露知识库缺口时，生成 knowledge update proposal。该节点只提出建议，不直接修改正式知识库。

## 8. RAG 检索链路

RAG 的目标是让回复可引用、可更新、可评测，而不是把企业知识写死进模型。

### document loading

`backend/rag/document_loader.py` 从 `data/kb_docs/` 加载 Markdown 文档，覆盖 API、billing、deployment、RAG、security 和 SOP。

### chunking

文档被切成带 metadata 的 chunks。每个 chunk 包含 `doc_id`、`chunk_id`、`title`、`source_path` 和正文片段，方便后续引用和 citation check。

### BM25

BM25 适合关键词精确匹配，例如 `429`、`quota exceeded`、`CUDA out of memory`、`permission denied`。

### hash-vector fallback

Hash-vector fallback 让项目在没有 `sentence-transformers` 依赖时仍能运行向量检索和评测。它不是最强语义检索方案，但适合本地可复现 demo。

### sentence-transformer embedding interface

系统提供 SentenceTransformer Embedding 接口，可以接入真实 embedding model，例如中文 embedding。可选依赖缺失时，系统会报告 unavailable，不会伪造结果。

### hybrid fusion

Hybrid retrieval 融合 BM25 和 vector retrieval，兼顾关键词命中和语义相似度。

### citation checker

Citation checker 检查 draft reply 是否引用了检索到的 evidence，帮助发现无引用回复、弱引用和错误引用。

### reranker interface

Reranker interface 支持 CrossEncoder Reranker，对候选 chunks 进行更精细排序。当前本地未安装可选依赖时，对应实验结果标记为 unavailable。

### RAG eval

RAG eval 关注：

- top-k hit：期望文档是否出现在前 k 个结果中。
- citation hit：期望引用是否被命中。
- latency：检索耗时。

当前 hard RAG eval 的 top-k hit 为 `0.72`，citation hit 为 `0.72`。这说明 RAG 是可用的，但仍是 End-to-End success 的瓶颈之一。

## 9. Tool Calling 设计

Tool Calling 是 ServiceOps Agent 区别于普通 RAG chatbot 的关键。工具调用不会停留在 prompt 文字层面，而是通过 `ToolRegistry` 执行后端函数并持久化：

- arguments：调用参数。
- result：工具返回结果。
- success/failure：是否成功。
- latency_ms：调用耗时。

当前工具是模拟企业系统的 mock tools：

| tool | 作用 |
| --- | --- |
| `check_api_status` | 根据 `request_id` 查询 API 请求状态、错误类型、延迟和区域 |
| `query_order_status` | 查询订单支付状态和 `quota_sync_status` |
| `get_customer_profile` | 查询客户套餐、剩余额度、QPS 限制、风险等级 |
| `get_deployment_status` | 查询部署状态、错误日志和 GPU 显存 |
| `get_sla_policy` | 根据 priority 查询 SLA 和升级策略 |
| `route_ticket` | 将工单路由到目标团队 |
| `create_approval_request` | 创建人工审批请求 |

生产化时，这些工具可以替换为真实 CRM、Billing、IAM、Observability、Deployment 和 Incident 系统。

## 10. Human-in-the-loop 设计

Human-in-the-loop 是系统的企业安全边界。以下情况需要人工介入：

- 涉及账号、订单、额度、退款、发票或套餐修改。
- 涉及隐私、审计、敏感数据或权限变更。
- 需要关闭工单、发送正式承诺、修改知识库。
- P0/P1 incident 或跨团队升级。
- Verifier 检测到 unsupported claims 或高风险动作。

系统不会把 Human Approval 当成失败，而是把它视为企业 Agent 的必要控制面。

## 11. Router LoRA 设计

Router LoRA 是 PEFT adapter，不是完整模型。它依赖 `Qwen/Qwen2.5-3B-Instruct` base model 加载。

Router 的学习目标是结构化分诊：

- `intent`
- `product`
- `priority`
- `suggested_team`
- `secondary_team`
- `missing_info`
- `required_tools`
- `needs_rag`
- `requires_human`
- `risk_level`

Router LoRA 训练后的核心结果：

- intent accuracy：`0.625 -> 0.8917`
- routing accuracy：`0.7167 -> 0.9917`
- requires-human accuracy：`0.9333`
- final eval_loss：`0.2099`

它的业务意义是让入口分流更稳定，减少错误路由和漏审批。

## 12. Verifier LoRA 设计

Verifier LoRA 是另一个独立 adapter，也依赖同一个 base model。它不负责写回复，而是负责校验回复是否安全、可信、可发出。

Verifier 学习字段：

- `supported_by_evidence`
- `unsupported_claims`
- `citation_errors`
- `contains_sensitive_action`
- `requires_approval`
- `risk_level`
- `decision`

Verifier LoRA 训练后的核心结果：

- support accuracy：`0.41 -> 0.99`
- false approval rate：`0.07 -> 0.0`
- unsupported claim recall：`0.97`
- final eval_loss：`0.2007`

false approval rate 是企业 Agent 的关键安全指标，因为“不该放行的回复被放行”会直接带来业务风险。

## 13. 评测体系

评测分四层：

- Router eval：衡量分类、路由、优先级、缺失信息、工具选择和人工审批判断。
- Verifier eval：衡量 evidence support、unsupported claim recall、citation error detection、risk recall 和 false approval rate。
- RAG eval：衡量 top-k hit、citation hit 和 latency。
- End-to-End eval：衡量完整工单生命周期，包括 tool recall、citation hit、unsupported claim rate、Human Approval 和 success rate。

当前必须明确区分两类结果：

- module-level LoRA：Router/Verifier adapter 在各自测试集上的指标。
- E2E LoRA runtime：完整 Agent Workflow 加载本地 base model 和 adapters 后的运行结果。

本地 base model 缺失或模型目录不完整时，不能用模块级指标冒充 E2E LoRA 已跑通。当前本机已补齐 base model，并完成 small LoRA E2E 验证；完整 LoRA E2E 仍建议在 GPU 上跑。

## 14. 本地运行与云端训练

GPU 训练已完成，两个 adapter 位于：

```text
outputs/router-lora-v1
outputs/verifier-lora-v1
```

这些目录是训练产物，应保留在本地或私有模型存储中，不提交 Git。

本地 LoRA demo 需要：

```text
models/Qwen2.5-3B-Instruct
outputs/router-lora-v1
outputs/verifier-lora-v1
```

下载 base model：

```bash
DOWNLOAD_BASE_MODEL=1 bash scripts/setup_local_model.sh
```

检查本地状态：

```bash
bash scripts/check_local_model.sh
```

baseline demo 不需要 base model：

```bash
bash scripts/run_local_demo_baseline.sh
```

LoRA demo 需要 base model：

```bash
bash scripts/run_local_demo_with_lora.sh
```

CPU/MPS 推理可能很慢，完整 LoRA E2E 更适合 GPU。训练已完成后，GPU 服务器可以释放，前提是 adapters 已同步本地并确认不需要继续跑 full E2E LoRA。

## 15. 当前限制与下一步

当前限制：

- 数据是 synthetic/manual holdout，不是生产数据。
- 企业工具是 mock tools，不连接真实生产系统。
- hard RAG eval 的 citation hit 为 `0.72`，检索仍是瓶颈。
- 本地 LoRA demo 已可运行，但 Mac MPS/CPU 推理速度明显慢于 GPU。
- manual holdout 样本量有限，不能代表生产泛化效果。

下一步：

- 在 GPU 上补跑完整 LoRA E2E，并与本地 small eval 结果区分报告。
- 在 GPU 环境补跑 full LoRA End-to-End eval。
- 接入真实 SentenceTransformer Embedding 和 CrossEncoder Reranker。
- 增加更多 manual negative cases，尤其是订单、额度、隐私、退款和 mixed-intent 场景。
- 强化 tool argument validation、metadata filtering、citation enforcement 和线上监控。
