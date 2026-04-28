# 本地模型检查

该报告用于判断本地是否已经具备 Router/Verifier LoRA 推理条件。Adapter 不能单独运行，必须和兼容的 base model 一起加载。

| 检查项 | 路径 | 状态 |
| --- | --- | --- |
| base_model_dir | `models/Qwen2.5-3B-Instruct` | found |
| config.json | `models/Qwen2.5-3B-Instruct/config.json` | found |
| base model weights | `models/Qwen2.5-3B-Instruct` | found |
| tokenizer files | `models/Qwen2.5-3B-Instruct` | found |
| router_adapter | `outputs/router-lora-v1` | found |
| verifier_adapter | `outputs/verifier-lora-v1` | found |

## 结论

- local_lora_inference_possible: true
- status: ready
- 说明：本地 base model、Router adapter、Verifier adapter 均已就绪，可以运行本地 LoRA smoke test。

注意：Adapter-only inference is impossible；Router/Verifier adapters 必须依赖 base model。
