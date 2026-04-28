# ServiceOps Agent Engineering Notes

This repository is intentionally built as a vertical enterprise AI system rather than a chatbot demo.

Core rules:

- Tool calls must execute backend functions and persist arguments, results, latency, and failures.
- Agent outputs must include traceable evidence from RAG chunks or business tools.
- Approval is required for sensitive account, billing, quota, close-ticket, and knowledge-base actions.
- Training targets are Router and Verifier adapters first. Do not fine-tune static enterprise knowledge into the model.
- Evaluation scripts compare prompt/rule baselines, LoRA outputs, RAG variants, tool-call accuracy, and end-to-end behavior.

Before handing work back:

- Run `python3 -m pytest -q`.
- Run Router eval: `python3 -m backend.evals.router_eval --dataset data/eval/router_eval_hard.jsonl` when the hard set exists, otherwise use `data/eval/router_eval.jsonl`.
- Run RAG eval: `python3 -m backend.evals.rag_eval --queries data/eval/rag_eval_hard.jsonl` when the hard set exists, otherwise use `data/eval/rag_eval.jsonl`.
- Run end-to-end eval: `python3 -m backend.evals.run_eval --dataset data/eval/end_to_end_eval_hard.jsonl` when the hard set exists, otherwise use `data/eval/end_to_end_eval.jsonl`.
- If dependencies are missing, update `pyproject.toml` and state exactly what was installed or skipped.

Repository hygiene:

- Never commit secrets, `.env`, SSH keys, API keys, tokens, customer data, or private endpoints.
- Training outputs must go under `outputs/` or `checkpoints/`; do not commit large model weights, adapters, `.safetensors`, `.bin`, `.pt`, or `.pth` files.
- Reports belong under `reports/`.
- Logs belong under `logs/` and should not be committed.
- Downloaded raw public datasets belong under `data/downloads/` and should not be committed unless explicitly curated.
- Data generation scripts must be deterministic. Every generator must accept a seed or use a fixed default seed.
- Do not auto-commit. If the repository has no baseline commit, remind the user to commit before large follow-up work.
