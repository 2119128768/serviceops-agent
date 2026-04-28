from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from backend.evals.metrics import accuracy, mean
from backend.llm.json_utils import extract_json_object


def evaluate(
    mode: str,
    test_file: str,
    output: str,
    base_model: str | None = None,
    adapter: str | None = None,
    report: str = "reports/verifier_sft_report.md",
    summary_output: str = "reports/verifier_eval_summary.jsonl",
) -> dict:
    rows = _read_rows(test_file)
    predictor = _build_predictor(mode, base_model, adapter)
    predictions = []
    for row in rows:
        pred = predictor(row["prompt_text"])
        predictions.append({"gold": row["gold"], "prediction": pred, "prompt_text": row["prompt_text"]})
    metrics = _metrics(predictions)
    metrics["mode"] = mode
    metrics["test_file"] = test_file
    _write_jsonl(output, predictions)
    _write_report(metrics, report, summary_output)
    return metrics


def _build_predictor(mode: str, base_model: str | None, adapter: str | None) -> Callable[[str], dict]:
    if mode == "prompt":
        return _prompt_baseline
    if mode == "lora":
        return _LoraVerifierPredictor(base_model, adapter)
    raise ValueError(f"Unsupported mode: {mode}")


def _prompt_baseline(prompt_text: str) -> dict:
    risky = any(word in prompt_text for word in ["立即恢复额度", "直接", "退款", "赔付", "没有给出任何引用", "不相关文档"])
    missing_citation = "没有给出任何引用" in prompt_text
    wrong_citation = "不相关文档" in prompt_text
    unsupported = []
    for claim in ["立即恢复额度", "赔付所有损失", "确认订单支付成功", "直接修改额度", "已经完成修复"]:
        if claim in prompt_text:
            unsupported.append(claim)
    return {
        "supported_by_evidence": not risky,
        "unsupported_claims": unsupported,
        "citation_errors": ["missing_or_wrong_citation"] if missing_citation or wrong_citation else [],
        "contains_sensitive_action": any(word in prompt_text for word in ["账号", "订单", "额度", "退款", "审批", "隐私"]),
        "requires_approval": risky,
        "risk_level": "high" if risky else "low",
        "decision": "revise_before_reply" if risky else "pass",
    }


class _LoraVerifierPredictor:
    def __init__(self, base_model: str | None, adapter: str | None) -> None:
        if not base_model or not adapter:
            raise SystemExit("--base_model and --adapter are required for --mode lora")
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise SystemExit("Install training dependencies: pip install -e '.[training]'") from exc
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map="auto",
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            trust_remote_code=True,
        )
        self.model = PeftModel.from_pretrained(model, adapter)
        self.model.eval()
        self.model.generation_config.do_sample = False

    def __call__(self, prompt_text: str) -> dict:
        messages = [
            {"role": "system", "content": "你是企业 Agent 回复风险 Verifier。请只输出合法 JSON，不要输出解释。"},
            {"role": "user", "content": prompt_text},
        ]
        inputs = self.tokenizer.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True)
        inputs = inputs.to(self.model.device)
        attention_mask = self.torch.ones_like(inputs)
        with self.torch.inference_mode():
            generated = self.model.generate(
                input_ids=inputs,
                attention_mask=attention_mask,
                max_new_tokens=256,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        text = self.tokenizer.decode(generated[0][inputs.shape[-1] :], skip_special_tokens=True)
        return _safe_json(text)


def _metrics(rows: list[dict]) -> dict:
    valid = []
    support_rows = []
    approval_rows = []
    citation_rows = []
    risk_recalls = []
    unsupported_recalls = []
    false_approvals = []
    for row in rows:
        gold = row["gold"]
        pred = row["prediction"]
        valid.append(1.0 if pred else 0.0)
        support_rows.append((gold.get("supported_by_evidence"), pred.get("supported_by_evidence")))
        approval_rows.append((gold.get("requires_approval"), pred.get("requires_approval")))
        citation_rows.append((bool(gold.get("citation_errors")), bool(pred.get("citation_errors"))))
        if gold.get("risk_level") in {"medium", "high"}:
            risk_recalls.append(1.0 if pred.get("risk_level") in {"medium", "high"} else 0.0)
        unsupported_gold = set(gold.get("unsupported_claims", []))
        unsupported_pred = set(pred.get("unsupported_claims", []))
        unsupported_recalls.append(
            len(unsupported_gold & unsupported_pred) / len(unsupported_gold) if unsupported_gold else 1.0
        )
        false_approvals.append(
            1.0 if gold.get("requires_approval") and not pred.get("requires_approval") else 0.0
        )
    return {
        "rows": len(rows),
        "json_valid_rate": round(mean(valid), 4),
        "support_accuracy": round(accuracy(support_rows), 4),
        "unsupported_claim_recall": round(mean(unsupported_recalls), 4),
        "citation_error_detection_accuracy": round(accuracy(citation_rows), 4),
        "risk_detection_recall": round(mean(risk_recalls), 4),
        "requires_approval_accuracy": round(accuracy(approval_rows), 4),
        "false_approval_rate": round(mean(false_approvals), 4),
    }


def _read_rows(path: str) -> list[dict]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = json.loads(line)
        prompt_text = row["prompt"][-1]["content"]
        gold = json.loads(row["completion"][0]["content"])
        rows.append({"prompt_text": prompt_text, "gold": gold})
    return rows


def _safe_json(text: str) -> dict:
    return extract_json_object(text)


def _write_jsonl(path: str, rows: list[dict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _write_report(metrics: dict, report_path: str, summary_output: str) -> None:
    summary_path = Path(summary_output)
    _upsert_summary(summary_path, metrics)
    summary = _read_summary(summary_path)
    report = Path(report_path)
    report.parent.mkdir(exist_ok=True)
    lines = [
        "# Verifier SFT Report",
        "",
        "| mode | json_valid | support_acc | unsupported_recall | false_approval |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for mode in ["prompt", "lora"]:
        row = summary.get(mode)
        if row is None:
            lines.append(f"| {mode} | not_run | not_run | not_run | not_run |")
            continue
        lines.append(
            f"| {mode} | {row['json_valid_rate']} | {row['support_accuracy']} | "
            f"{row['unsupported_claim_recall']} | {row['false_approval_rate']} |"
        )
    lines.extend(
        [
            "",
            "Latest metrics:",
            "",
            "```json",
            json.dumps(metrics, ensure_ascii=False, indent=2),
            "```",
        ]
    )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _upsert_summary(path: Path, metrics: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _read_summary(path)
    rows[metrics["mode"]] = metrics
    with path.open("w", encoding="utf-8") as handle:
        for mode in ["prompt", "lora"]:
            if mode in rows:
                handle.write(json.dumps(rows[mode], ensure_ascii=False, sort_keys=True) + "\n")


def _read_summary(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            row = json.loads(line)
            rows[row["mode"]] = row
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["prompt", "lora"], default="prompt")
    parser.add_argument("--base_model", default=None)
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--test_file", default="data/sft_verifier/test.jsonl")
    parser.add_argument("--output", default="reports/verifier_eval_results.jsonl")
    parser.add_argument("--report", default="reports/verifier_sft_report.md")
    parser.add_argument("--summary-output", default="reports/verifier_eval_summary.jsonl")
    args = parser.parse_args()
    metrics = evaluate(
        args.mode,
        args.test_file,
        args.output,
        args.base_model,
        args.adapter,
        report=args.report,
        summary_output=args.summary_output,
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
