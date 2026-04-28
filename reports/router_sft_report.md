# Router SFT Report

本报告是 Router 的 module-level evaluation，评测数据为 `data/sft_router/test.jsonl`。Router 的职责是把自然语言工单转成结构化 JSON，用于后续路由、RAG、Tool Calling 和 Human Approval。

## 指标结果

| mode | json_valid | intent_acc | priority_acc | routing_acc | missing_f1 | tools_acc | human_acc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Rule Router | 1.0 | 0.625 | 0.85 | 0.7167 | 0.8 | 0.725 | 0.85 |
| Prompt Router | 1.0 | 0.625 | 0.85 | 0.7167 | 0.8 | 0.725 | 0.85 |
| Router LoRA | 1.0 | 0.8917 | 0.9583 | 0.9917 | 0.7639 | 0.8167 | 0.9333 |

Training/evaluation note：

- Final Router LoRA eval_loss：`0.2099`，来自 `logs/router_train.log`。
- LoRA metrics 在 GPU training host 产出，并保存在 `reports/router_eval_summary.jsonl`。
- Router adapter 位于 `outputs/router-lora-v1`，该目录被 Git 忽略，不应提交权重。

## 指标解释

intent accuracy 表示 Router 是否判断对工单意图，例如 `api_quota_error`、`deployment_failure`、`security_privacy`。它决定后续查什么知识、调用什么工具、由哪个团队处理。

routing accuracy 表示 Router 是否把工单分到正确团队，例如 `platform_support`、`billing_system`、`model_serving`、`security_ops`。在企业支持系统中，路由错误会直接带来响应延迟和跨团队转派成本。

requires-human accuracy 表示 Router 是否识别出需要人工审批的工单。涉及账号、订单、额度、退款、隐私和权限时，漏掉审批比多走一次审批更危险。

missing-info F1 表示缺失字段识别质量，例如 `request_id`、`account_id`、`order_id`、`deployment_id`。该指标没有随 LoRA 同步上升，说明后续仍可补充更多字段级监督样本。

tools accuracy 表示 Router 选择业务工具的准确率。Tool Calling 决定 Agent 是否真正查询后端状态，而不是只生成泛泛回复。

## 结果解读

Router LoRA 将 intent accuracy 从 `0.625` 提升到 `0.8917`，将 routing accuracy 从 `0.7167` 提升到 `0.9917`，说明微调显著提升了结构化分诊能力。对企业工单系统来说，这意味着入口处的自动分流更可靠，后续 RAG、工具调用和审批链路更容易走到正确分支。

需要注意的是，这是 module-level 指标。它证明 Router adapter 在 Router 测试集上有效，但不能直接等同于完整 Agent Workflow 的 End-to-End success。E2E 还受到 RAG citation、工具参数、Verifier 判断和状态流影响。
