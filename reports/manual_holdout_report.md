# Manual Holdout Report

Manual holdout 数据来自 `data_pipeline/build_manual_holdout.py` 中人工整理的企业支持案例。它不是生产数据，也不是直接复制 synthetic ticket generator 的输出。

manual holdout 的作用是测试模板外泛化：让系统面对更口语、更混合、更缺字段、更接近真实支持场景的输入，观察 Router、Verifier 和完整 Agent Workflow 是否仍然稳定。

| split | rows | purpose |
| --- | ---: | --- |
| Router | 50 | noisy/mixed Chinese ticket classification and routing |
| Verifier | 50 | evidence support, citation, overpromise, approval, and sensitive-action checks |
| E2E | 30 | full workflow behavior on manually curated cases |

## Router Manual Holdout

| mode | intent | routing | priority | missing_f1 | tools | human |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| rule | 0.8 | 0.86 | 0.92 | 0.9267 | 0.88 | 0.92 |

解释：

- intent `0.8` 表示 rule Router 在人工样本上能识别大部分意图，但 mixed-intent 和模糊工单仍会混淆。
- routing `0.86` 表示团队分派总体可用，但跨团队场景仍需要更强 taxonomy 约束。
- human `0.92` 表示需要审批的风险场景大多能被识别。

## Verifier Manual Holdout

| mode | support | unsupported_recall | citation | risk_recall | approval | false_approval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| prompt | 0.12 | 1.0 | 0.5 | 0.5128 | 0.3 | 0.38 |

解释：

- prompt Verifier 在人工 holdout 上 support accuracy 只有 `0.12`，说明仅靠 prompt 很难稳定判断回复是否真正被证据支持。
- unsupported recall 为 `1.0`，说明它较敏感，但这不代表整体判断好，因为 approval 和 citation 仍较弱。
- false approval 为 `0.38`，这是明显风险：很多不该放行的回复被放行。

这个结果强化了 Verifier LoRA 的必要性。module-level Verifier LoRA 在测试集上将 support accuracy 提升到 `0.99`，false approval rate 降到 `0.0`。当前本地 base model 已补齐，并已跑通 5 条 small LoRA E2E；完整 manual holdout LoRA E2E 仍建议在 GPU 上补跑。

## E2E Manual Holdout

| mode | sample_count | intent | routing | tool_recall | citation | human | success | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| direct_llm | 30 | 0.8333 | 0.9 | 0.0 | 0.0 | 1.0 | 0.0 | ok |
| rag_only | 30 | 0.8333 | 0.9 | 0.0 | 0.6 | 1.0 | 0.0 | ok |
| agent_rule_router_prompt_verifier | 30 | 0.8333 | 0.9 | 0.8333 | 0.6333 | 0.9667 | 0.3 | ok |
| agent_router_lora_prompt_verifier | 30 | n/a | n/a | n/a | n/a | n/a | n/a | unavailable: Install LoRA runtime dependencies with: pip install -e '.[training]' |
| agent_router_lora_verifier_lora | 30 | n/a | n/a | n/a | n/a | n/a | n/a | unavailable: Install LoRA runtime dependencies with: pip install -e '.[training]' |

解释：

- direct LLM 没有工具调用和引用，因此 success 为 `0.0`。
- rag_only 有 citation 提升，但没有工具和状态流，因此仍不能完成完整工单处理。
- agent_rule_router_prompt_verifier 的 success 为 `0.3`，说明 workflow 有明显增益，但 citation 和 tool coverage 仍是瓶颈。

## 限制

- manual holdout 仍是小规模人工集合，不代表生产分布。
- 当前本地 LoRA E2E 未跑通时，不能用 manual holdout 推断 LoRA 在完整链路的效果。
- mock tools 的覆盖范围有限，部分真实企业工具链路没有实现。
- 后续需要扩展更多 mixed-intent、low-evidence、overpromise、privacy 和 billing negative cases。
