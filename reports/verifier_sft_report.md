# Verifier SFT Report

本报告是 Verifier 的 module-level evaluation，评测数据为 `data/sft_verifier/test.jsonl`。Verifier 的职责不是写回复，而是在回复发出前检查 evidence support、unsupported claims、citation errors、sensitive actions 和 approval decision。

## 指标结果

| mode | json_valid | support_acc | unsupported_recall | citation_acc | risk_recall | approval_acc | false_approval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Prompt Verifier | 1.0 | 0.41 | 0.7783 | 1.0 | 0.9091 | 0.61 | 0.07 |
| Verifier LoRA | 1.0 | 0.99 | 0.97 | 0.96 | 0.987 | 0.99 | 0.0 |

Training/evaluation note：

- Final Verifier LoRA eval_loss：`0.2007`，来自 `logs/verifier_train.log`。
- LoRA metrics 在 GPU training host 产出，并保存在 `reports/verifier_eval_summary.jsonl`。
- Verifier adapter 位于 `outputs/verifier-lora-v1`，该目录被 Git 忽略，不应提交权重。

## 指标解释

support accuracy 表示 Verifier 是否正确判断回复是否被 evidence 和 tool results 支持。这个指标越高，说明系统越能区分“有依据的回复”和“看起来合理但没有证据的回复”。

unsupported claim recall 表示 Verifier 对无依据结论的召回能力。例如回复中声称“订单已支付”“额度已恢复”“问题已经修复”，但 evidence 或 tool results 没有支持，就应该被识别出来。

citation accuracy 表示 Verifier 对引用问题的识别能力。企业 Agent 不能只给流畅回答，还要能说明依据来自哪些知识库 chunk 或业务工具结果。

risk recall 表示 Verifier 对敏感动作和高风险场景的识别能力，覆盖账号、订单、额度、退款、隐私和权限等风险。

false approval rate 表示不该被放行的回复被错误放行的比例。这个指标在企业 Agent 安全中非常关键，因为错误放行可能导致越权承诺、隐私泄露或业务误操作。

## 结果解读

Verifier LoRA 将 support accuracy 从 `0.41` 提升到 `0.99`，unsupported claim recall 提升到 `0.97`，false approval rate 从 `0.07` 降到 `0.0`。这说明 Verifier adapter 对证据支持和风险放行的判断明显强于 prompt baseline。

需要注意的是，Verifier LoRA 的 module-level 结果不能自动代表完整系统端到端效果。完整 Agent 仍依赖 RAG 是否检索到证据、工具是否返回正确状态、draft reply 是否包含可校验引用，以及本地是否具备 base model 来运行 LoRA runtime。
