# ServiceOps Agent：企业智能工单与知识运维 Agent 平台

**Enterprise Ticket Automation with Agentic RAG, LoRA Fine-tuning and LLMOps**

ServiceOps Agent 是一个面向 AI 平台、企业软件和技术支持团队的智能工单自动化系统。它不是一个简单 chatbot，也不是只把用户问题丢给 LLM 生成回复的 demo，而是围绕企业工单处理链路设计的 Agent 平台：工单进入系统后，会经历分类路由、缺失信息识别、RAG 检索、历史工单匹配、Tool Calling、处理方案规划、回复草稿生成、Verifier 风险校验、Human-in-the-loop 审批和知识库更新建议。

项目数据和业务系统均为可复现实验环境：synthetic tickets 是构造数据，manual holdout 是人工整理评测集，企业工具调用连接的是 mock database，不连接真实客户、订单、账号或计费系统。项目目标是展示一个工程化、可评测、可解释的 LLM 应用系统。

## 1. 项目简介

企业技术支持不是单轮问答。一个看似简单的 “API 返回 429” 工单，可能同时涉及 API 错误码、账号套餐、订单支付、额度同步、SLA、历史类似工单和是否允许自动回复。ServiceOps Agent 将这些能力拆成可观测的工作流节点：

- Ticket System：创建、查询、流转工单，保存状态和事件。
- Router：输出 intent、priority、suggested_team、secondary_team、missing_info、required_tools、requires_human。
- RAG Retriever：检索企业知识库、SOP、错误码文档和历史工单。
- Tool Caller：查询 API 请求、订单、账号、部署状态和 SLA 策略。
- Planner：根据证据和工具结果生成排查步骤。
- Writer：生成用户回复草稿和内部处理说明。
- Verifier：检查证据支持、错误引用、unsupported claims、敏感动作和审批需求。
- Human Approval：对账号、订单、额度、退款、关闭工单、知识库修改等动作进行人工审批。
- Evaluation：评测 Router、Verifier、RAG、End-to-End Agent 和 manual holdout。

系统设计原则是：企业知识用 RAG 管理，稳定决策用 Router/Verifier LoRA 学习，风险动作交给 Human-in-the-loop 控制。

## 2. 解决的问题

企业支持团队常见痛点包括：

- 重复支持工单多，人工分诊慢。
- 知识散落在错误码文档、SOP、历史工单和部署手册中。
- 客户回复风格不一致，容易漏掉关键追问或证据引用。
- 普通 LLM 容易流畅地过度承诺，例如“订单已支付”“额度马上恢复”“问题已经修复”。
- 账号、订单、额度、退款、隐私和生产事故等场景必须有人工审批。
- 团队需要 evidence-grounded replies，也就是回复能追溯到知识库证据或业务工具结果。
- 工程团队需要知道 Agent 为什么成功、为什么失败，以及失败发生在 Router、RAG、Tool Calling 还是 Verifier。

ServiceOps Agent 的核心价值不是“替客服写几句话”，而是把工单处理流程变成可运行、可审计、可评测的系统。

## 3. 系统整体架构

```text
用户提交工单
   ↓
FastAPI 工单系统
   ↓
Agent Workflow
   ├── Router：分类 / 优先级 / 路由 / 缺失信息 / 工具选择
   ├── RAG Retriever：企业知识库与历史工单检索
   ├── Tool Caller：账号、订单、API 请求、部署状态查询
   ├── Planner：处理步骤与排查方案
   ├── Writer：用户回复草稿
   ├── Verifier：证据校验、风险校验、审批判断
   └── Human Approval：高风险动作人工审批
   ↓
工单状态更新 / 回复草稿 / 审批请求 / 知识库更新建议
   ↓
Eval & Reports
```

技术栈：

- Backend：`FastAPI`, `SQLAlchemy`, `Pydantic`
- Agent Workflow：自定义状态流，节点可观测、可替换
- RAG：BM25、hash-vector fallback、hybrid retrieval、可选 SentenceTransformer Embedding、可选 CrossEncoder Reranker、citation checker
- Tool Calling：执行后端函数并记录 arguments、result、latency、success/failure
- Training：`Transformers`, `Datasets`, `PEFT`, `TRL`, `Accelerate`, `QLoRA`
- Runtime：baseline local demo、本地 LoRA runtime、adapter validation、smoke test
- Evaluation：Router eval、Verifier eval、RAG eval、End-to-End eval、manual holdout、failure analysis

## 4. 核心模块详解

### Ticket System

`backend/api/tickets.py` 和 `backend/ticketing/` 提供工单创建、查询、运行 Agent、查看 trace 的 API。工单不只是保存一段文本，还会记录 intent、priority、suggested_team、risk_level、missing_info、status、最终回复和内部摘要。

### Database Models

`backend/database/models.py` 定义 tickets、ticket_events、tool_calls、retrieved_chunks、approval_requests、knowledge_updates 等表。每次 RAG 检索、工具调用、审批请求和状态变化都可以落库，方便审计、复盘和评测。

### RAG System

`backend/rag/` 负责文档加载、chunking、BM25、向量检索、hybrid fusion、reranker 接口和 citation checker。RAG 用来管理变化快的企业知识，例如错误码说明、额度同步策略、RAG 导入排查、GPU 显存建议和客户回复 SOP。它的输出是 evidence，不是最终答案。

### Agent Workflow

`backend/agents/graph.py` 将工单处理拆成清晰节点：

```text
classify_ticket
→ check_missing_info
→ retrieve_knowledge
→ retrieve_similar_tickets
→ call_tools
→ plan_solution
→ draft_reply
→ verify_response
→ request_approval
→ update_knowledge
```

这种拆分让系统能回答三个关键问题：哪一步做了什么，为什么要这么做，失败时应该改哪个模块。

### Tool Calling

`backend/tools/` 模拟企业内部系统：

- `check_api_status`：根据 `request_id` 查询 API 请求状态。
- `query_order_status`：根据 `order_id` 或 `account_id` 查询订单和 `quota_sync_status`。
- `get_customer_profile`：查询套餐、剩余额度、QPS 限制和账号风险等级。
- `get_deployment_status`：查询部署状态、错误日志和 GPU 显存。
- `get_sla_policy`：查询优先级对应的响应和升级策略。
- `route_ticket`：记录路由到目标团队的动作。
- `create_approval_request`：创建人工审批请求。

这些工具是真实执行的后端函数，但数据源是 mock database，因此不能把它描述成连接了真实企业系统。

### Human Approval

Human Approval 是企业 Agent 的安全边界。只要涉及账号、订单、额度、退款、发票、隐私、关闭工单或知识库修改，系统就不会直接自动执行，而是创建 approval request。这样既保留自动化效率，也避免 LLM 越权。

### Router LoRA

Router LoRA 学习结构化分诊能力，目标不是写漂亮回复，而是稳定输出 JSON：intent、priority、team、missing_info、required_tools、needs_rag、requires_human 和 risk_level。它对应企业工单入口的“分流器”。

### Verifier LoRA

Verifier LoRA 学习风险校验能力，判断 draft reply 是否被 evidence 支持、是否有 unsupported claims、是否引用错误、是否包含敏感动作、是否需要审批。它是 Agent 回复正式发出前的安全闸门。

### Evaluation System

`backend/evals/` 和 `training/evaluate_*.py` 覆盖模块级和链路级评测：

- Router：JSON valid rate、intent accuracy、routing accuracy、priority accuracy、missing-info F1、tool accuracy、requires-human accuracy。
- Verifier：support accuracy、unsupported claim recall、citation error detection、risk recall、approval accuracy、false approval rate。
- RAG：top-k hit、citation hit、latency。
- End-to-End：tool recall、citation hit、unsupported claim rate、success rate、latency、tool calls。

### Local Runtime

baseline demo 可以直接在本地运行，不依赖大模型。LoRA demo 需要 `Qwen/Qwen2.5-3B-Instruct` base model 和两个 adapter：

- `outputs/router-lora-v1`
- `outputs/verifier-lora-v1`

Adapter 不是完整模型，不能单独推理。如需运行 LoRA demo，需要先准备 base model 和 adapters，并通过 `bash scripts/check_local_model.sh` 检查。

## 5. 项目目录结构

```text
serviceops-agent/
├── backend/
│   ├── api/                 # FastAPI routes：tickets、approvals、rag、evals、metrics
│   ├── agents/              # Agent Workflow、state、nodes
│   ├── agents/nodes/        # classify、retrieve、tool、plan、draft、verify、approval
│   ├── database/            # SQLAlchemy models、schemas、session、seed
│   ├── evals/               # E2E、RAG、Router eval 和指标
│   ├── llm/                 # Router/Verifier baseline、LoRA runtime、JSON utils
│   ├── rag/                 # document loader、BM25、vector、hybrid、reranker、citation checker
│   ├── tools/               # 模拟业务工具调用
│   └── tracing/             # event recorder 和 trace logger
├── data/
│   ├── eval/                # hard eval 和 manual holdout
│   ├── kb_docs/             # 企业知识库 Markdown 文档
│   ├── sft_router/          # Router SFT train/val/test
│   ├── sft_verifier/        # Verifier SFT train/val/test
│   ├── synthetic_tickets/   # 1200 条中文 synthetic tickets
│   └── taxonomy/            # 15 intent taxonomy
├── data_pipeline/           # deterministic 数据生成、SFT 构造、报告写入脚本
├── training/                # QLoRA 训练和模块评测脚本
├── reports/                 # 架构、实验、失败分析和运行说明
├── scripts/                 # demo、eval、adapter check、本地模型 setup
├── frontend/                # 本地 Web console
├── outputs/                 # LoRA adapter，本地存在但被 Git 忽略
├── models/                  # base model，本地可选但被 Git 忽略
├── model_cache/             # 模型缓存，被 Git 忽略
├── logs/                    # 训练和运行日志，被 Git 忽略
└── checkpoints/             # 训练 checkpoint，被 Git 忽略
```

## 6. 数据构造

项目数据围绕企业 AI 平台支持场景构造：

- 15 intent taxonomy：覆盖 `api_quota_error`、`api_rate_limit_error`、`api_auth_error`、`quota_billing`、`rag_import_error`、`rag_quality_issue`、`deployment_failure`、`gpu_memory_error`、`security_privacy`、`permission_issue`、`account_issue`、`model_latency`、`feature_request`、`incident_outage`、`ambiguous_missing_info` 等场景。
- 1200 条中文 synthetic tickets：用于构造 Router/Verifier 训练集和 hard eval。
- Router SFT data：从工单文本到结构化 Router JSON。
- Verifier SFT data：从 ticket、evidence、tool results、draft reply 到风险校验 JSON。
- hard eval：加入混合意图、缺失信息、无答案、过度承诺等难例。
- manual holdout：人工整理的 Router 50 条、Verifier 50 条、E2E 30 条，用于测试模板外泛化。

限制说明：synthetic tickets 是构造数据，不代表真实生产流量；manual holdout 是人工整理评测集，不是客户数据。

## 7. 微调设计

- Base model：`Qwen/Qwen2.5-3B-Instruct`
- 方法：QLoRA
- Router adapter：`outputs/router-lora-v1`
- Verifier adapter：`outputs/verifier-lora-v1`

设计取舍：

- Router LoRA 学分类、路由、缺失信息、工具选择和 Human Approval 判断。
- Verifier LoRA 学 evidence support、unsupported claim、citation error、risk 和 approval decision。
- 企业知识不写进 LoRA，因为知识变化快，应该由 RAG 管理。
- Writer 不作为第一优先微调对象，因为 Writer 越强不一定越安全，可能更擅长生成流畅但无依据的内容。
- Router 和 Verifier 是两个独立 adapters，便于分别评测和替换。

## 8. 实验结果

### Router LoRA

| 指标 | baseline | Router LoRA |
| --- | ---: | ---: |
| intent accuracy | 0.625 | 0.8917 |
| routing accuracy | 0.7167 | 0.9917 |
| requires-human accuracy | 0.85 | 0.9333 |
| final eval_loss | n/a | 0.2099 |

Router LoRA 的意义是让企业工单入口更稳定：分类更准、路由更准、高风险工单更容易被送入人工审批链路。

### Verifier LoRA

| 指标 | prompt baseline | Verifier LoRA |
| --- | ---: | ---: |
| support accuracy | 0.41 | 0.99 |
| false approval rate | 0.07 | 0.0 |
| unsupported claim recall | 0.7783 | 0.97 |
| final eval_loss | n/a | 0.2007 |

Verifier LoRA 的关键价值是降低 false approval rate，也就是减少“不该放行的回复被放行”。

### RAG

| variant | top-k hit | citation hit |
| --- | ---: | ---: |
| BM25 only | 0.50 | 0.50 |
| Hash-vector only | 0.72 | 0.72 |
| Hybrid | 0.72 | 0.72 |

hard RAG eval top-k hit 为 `0.72`，citation hit 为 `0.72`。这说明 RAG 已经能提供有效证据，但 citation miss 仍是 End-to-End 成功率瓶颈之一。

### End-to-End 说明

End-to-End eval 测的是完整工单生命周期，而不是单个 LoRA 模块。当前 rule-agent 在 synthetic hard eval 上 success 为 `0.4667`，manual holdout E2E success 为 `0.3`。本地 LoRA runtime 已接入并完成小规模验证：`agent_router_lora_verifier_lora` 在 `data/eval/manual_holdout_e2e.jsonl` 上跑通 5 条样本。完整 LoRA E2E 仍建议在 GPU 上补跑。

## 9. 如何运行

### 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

如需训练、加载 LoRA 或运行本地 LoRA eval：

```bash
python3 -m pip install -e ".[training]"
```

如需真实 SentenceTransformer Embedding 或 CrossEncoder Reranker：

```bash
python3 -m pip install -e ".[rag]"
```

### baseline local demo

baseline demo 不需要 base model，也不需要 GPU：

```bash
bash scripts/run_local_demo_baseline.sh
```

打开：

- Frontend：`http://127.0.0.1:8000/`
- API docs：`http://127.0.0.1:8000/docs`

### local LoRA setup

准备本地目录和依赖：

```bash
bash scripts/setup_local_model.sh
```

下载 base model：

```bash
DOWNLOAD_BASE_MODEL=1 bash scripts/setup_local_model.sh
```

检查 base model 和 adapters：

```bash
bash scripts/check_local_model.sh
```

Adapter validation：

```bash
bash scripts/validate_adapters.sh
```

Smoke test：

```bash
bash scripts/run_local_lora_smoke_test.sh
```

LoRA demo：

```bash
bash scripts/run_local_demo_with_lora.sh
```

小规模 LoRA E2E eval：

```bash
bash scripts/run_local_lora_eval_small.sh
```

CPU/MPS 推理可能很慢，完整 LoRA E2E 更适合在 GPU 环境运行。

### 运行评测

```bash
python3 -m pytest -q
bash scripts/run_v1_evals.sh
bash scripts/check_project_ready.sh
```

单独运行 End-to-End eval：

```bash
python3 -m backend.evals.run_eval \
  --dataset data/eval/end_to_end_eval_hard.jsonl \
  --mode all \
  --limit 30
```

本地 LoRA E2E 示例，前提是 base model 已存在：

```bash
python3 -m backend.evals.run_eval \
  --dataset data/eval/manual_holdout_e2e.jsonl \
  --mode agent_router_lora_verifier_lora \
  --use-local-lora \
  --base-model-path models/Qwen2.5-3B-Instruct \
  --router-adapter outputs/router-lora-v1 \
  --verifier-adapter outputs/verifier-lora-v1 \
  --limit 5
```
