# 本地 LoRA Runtime 说明

## 1. 为什么 adapter 不能单独运行

Router LoRA 和 Verifier LoRA 都是 PEFT adapter，也就是挂在 base model 之上的增量权重。Adapter 只保存任务相关的低秩增量参数，不包含完整语言模型参数、tokenizer、词表、位置编码或生成能力。

因此：

- `outputs/router-lora-v1` 不能单独推理。
- `outputs/verifier-lora-v1` 不能单独推理。
- 必须先加载兼容的 `Qwen/Qwen2.5-3B-Instruct` base model，再加载 adapter。

一句话：Adapter-only inference is impossible。

## 2. 本地运行 LoRA 需要什么

本地 LoRA demo 需要以下三部分同时存在：

```text
models/Qwen2.5-3B-Instruct
outputs/router-lora-v1
outputs/verifier-lora-v1
```

也可以通过环境变量指定 base model：

```bash
LOCAL_BASE_MODEL_PATH=/path/to/Qwen2.5-3B-Instruct
```

当前本地检查结果以 `bash scripts/check_local_model.sh` 为准。本轮检查显示：

- `Qwen2.5-3B-Instruct` base model directory：存在
- `Qwen2.5-3B-Instruct` base model weights：完整
- `outputs/router-lora-v1`：存在
- `outputs/verifier-lora-v1`：存在
- local LoRA inference possible：true
- local LoRA smoke test：已通过
- local LoRA small E2E：已通过 5 条样本

本机已经具备本地 LoRA 推理条件。完整 E2E 仍建议在 GPU 上补跑，因为 Mac MPS/CPU 运行 3B 模型会明显慢。

## 3. baseline demo 不需要基础模型

如果只是展示完整工单流程、RAG、Tool Calling、Human Approval、trace 和前端 console，可以直接运行 baseline demo：

```bash
bash scripts/run_local_demo_baseline.sh
```

baseline demo 不需要 GPU，也不需要下载 `Qwen/Qwen2.5-3B-Instruct`。

## 4. LoRA demo 需要下载或同步基础模型

下载 base model：

```bash
DOWNLOAD_BASE_MODEL=1 bash scripts/setup_local_model.sh
```

如果 base model 已经在服务器上，可以同步到本机。脚本只使用环境变量，不保存密码：

```bash
REMOTE_HOST=root@your-server \
REMOTE_MODEL_DIR=/root/models/Qwen2.5-3B-Instruct \
bash scripts/sync_base_model_from_server.sh
```

不要把服务器密码、SSH private key、token 或任何 secret 写入脚本或文档。

## 5. 检查命令

```bash
bash scripts/check_local_model.sh
```

该命令会检查：

- base model directory 是否存在。
- `config.json` 是否存在。
- tokenizer files 是否存在。
- Router adapter 是否存在。
- Verifier adapter 是否存在。

报告会写入：

```text
reports/local_model_check.md
```

如果 base model 缺失，脚本会显示 `base_model_missing_or_incomplete`。当前本机检查显示 `ready`。

## 6. smoke test

下载或同步 base model 后运行：

```bash
bash scripts/run_local_lora_smoke_test.sh
```

smoke test 会做最小闭环：

- 加载 `Qwen2.5-3B-Instruct` base model。
- 加载 Router adapter。
- 加载 Verifier adapter。
- 对一条 429 quota 工单跑 Router。
- 对一个 unsupported-claim payload 跑 Verifier。
- 将结果写入 `reports/local_lora_smoke_test.md`。

当前 smoke test 已真实通过，并写入 `reports/local_lora_smoke_test.md`。

## 7. baseline demo

```bash
bash scripts/run_local_demo_baseline.sh
```

用途：

- 本地展示 FastAPI 工单系统。
- 展示 Agent Workflow、RAG、mock tools、approval 和 trace。
- 不依赖 GPU 或 base model。

## 8. LoRA demo

```bash
bash scripts/run_local_demo_with_lora.sh
```

用途：

- 在本地加载 Router LoRA 和 Verifier LoRA。
- 用 adapters 替换 baseline Router/Verifier。
- 展示本地 LoRA runtime。

前提：

- `bash scripts/check_local_model.sh` 显示 ready。
- 已安装 training/runtime 依赖。
- base model 和 adapters 均在本地。

## 9. 本地 LoRA 小规模 E2E

```bash
bash scripts/run_local_lora_eval_small.sh
```

该脚本用于补跑小规模 E2E LoRA 检查。它不是重新训练，只是加载本地 base model 和 adapters 运行评测。

## 10. CPU/MPS 性能预期

- CPU 可以尝试，但推理可能非常慢。
- Apple Silicon MPS 可以尝试，但性能和兼容性取决于 PyTorch、Transformers 和模型大小。
- 16GB RAM 可能紧张。
- 32GB RAM 更稳。
- full LoRA E2E eval 更适合 GPU。

## 11. GPU 服务器是否可以释放

Router LoRA 和 Verifier LoRA 已完成训练，adapter 已存在于本地 `outputs/` 目录。只要确认 adapter 已同步本地，且不需要继续跑 full LoRA End-to-End eval，GPU 服务器可以释放。

如果还需要补跑完整 LoRA E2E，建议暂时保留 GPU 或在云端重新挂载 base model 和 adapters。

## 12. Git 安全

不要提交：

- `models/`
- `outputs/`
- `model_cache/`
- `hf_cache/`
- `logs/`
- `checkpoints/`
- `.env`
- `*.safetensors`
- `*.bin`
- `*.pt`
- `*.pth`

可以提交：

- runtime 代码。
- setup/check/demo 脚本。
- README。
- reports。
- eval sets。
- `.env.example`，前提是不包含真实 secrets。

发布前检查：

```bash
git ls-files | grep -E "outputs/|models/|model_cache/|logs/|\\.safetensors|\\.bin|\\.pt|\\.pth|\\.env" || true
```

如果只出现 `.env.example`，需要人工确认它只是示例配置；真实 `.env` 不应出现。
