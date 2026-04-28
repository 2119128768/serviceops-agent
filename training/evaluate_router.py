from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from backend.evals.metrics import accuracy, mean
from backend.llm.json_utils import extract_json_object
from backend.llm.router_model import RouterModel


def evaluate(
    mode: str,
    test_file: str,
    output: str,
    base_model: str | None = None,
    adapter: str | None = None,
    report: str = "reports/router_sft_report.md",
    summary_output: str = "reports/router_eval_summary.jsonl",
) -> dict[str, Any]:
    rows = _read_router_rows(test_file)
    predictor = _build_predictor(mode, base_model=base_model, adapter=adapter)
    predictions = []
    for row in rows:
        pred = predictor(row["ticket"])
        predictions.append({"ticket": row["ticket"], "gold": row["gold"], "prediction": pred})

    metrics = _metrics(predictions)
    metrics["mode"] = mode
    metrics["test_file"] = test_file
    _write_jsonl(output, predictions)
    _write_report(metrics, report, summary_output)
    return metrics


def _build_predictor(mode: str, base_model: str | None, adapter: str | None) -> Callable[[str], dict]:
    if mode in {"rule", "prompt"}:
        router = RouterModel()
        return router.classify
    if mode == "lora":
        return _LoraRouterPredictor(base_model, adapter)
    raise ValueError(f"Unsupported mode: {mode}")


class _LoraRouterPredictor:
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

    def __call__(self, ticket: str) -> dict:
        messages = [
            {"role": "system", "content": "你是企业技术支持工单 Router。请只输出合法 JSON，不要输出解释。"},
            {"role": "user", "content": f"工单：{ticket}"},
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
    json_valid = []
    intent_rows = []
    priority_rows = []
    routing_rows = []
    tool_rows = []
    human_rows = []
    missing_precision = []
    missing_recall = []
    missing_f1 = []

    for row in rows:
        gold = row["gold"]
        pred = row["prediction"]
        valid = bool(pred)
        json_valid.append(1.0 if valid else 0.0)
        intent_rows.append((gold.get("intent"), pred.get("intent")))
        priority_rows.append((gold.get("priority"), pred.get("priority")))
        routing_rows.append((gold.get("suggested_team"), pred.get("suggested_team", "").split(",")[0]))
        tool_rows.append((set(gold.get("required_tools", [])), set(pred.get("required_tools", []))))
        human_rows.append((gold.get("requires_human"), pred.get("requires_human")))
        p, r, f = _set_prf(gold.get("missing_info", []), pred.get("missing_info", []))
        missing_precision.append(p)
        missing_recall.append(r)
        missing_f1.append(f)

    return {
        "rows": len(rows),
        "json_valid_rate": round(mean(json_valid), 4),
        "intent_accuracy": round(accuracy(intent_rows), 4),
        "priority_accuracy": round(accuracy(priority_rows), 4),
        "routing_accuracy": round(accuracy(routing_rows), 4),
        "missing_info_precision": round(mean(missing_precision), 4),
        "missing_info_recall": round(mean(missing_recall), 4),
        "missing_info_f1": round(mean(missing_f1), 4),
        "required_tools_accuracy": round(mean([1.0 if exp == pred else 0.0 for exp, pred in tool_rows]), 4),
        "requires_human_accuracy": round(accuracy(human_rows), 4),
    }


def _set_prf(expected: list[str], predicted: list[str]) -> tuple[float, float, float]:
    exp = set(expected)
    pred = set(predicted)
    tp = len(exp & pred)
    precision = tp / len(pred) if pred else (1.0 if not exp else 0.0)
    recall = tp / len(exp) if exp else 1.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def _read_router_rows(path: str) -> list[dict]:
    raw = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]
    rows = []
    for row in raw:
        if "prompt" in row:
            ticket = row["prompt"][-1]["content"].removeprefix("工单：")
            gold = json.loads(row["completion"][0]["content"])
        else:
            ticket = row["ticket"]
            gold = {
                "intent": row["intent"],
                "priority": row["priority"],
                "suggested_team": row["suggested_team"],
                "missing_info": row.get("missing_info", []),
                "required_tools": row.get("required_tools", []),
                "requires_human": row.get("requires_human", False),
            }
        rows.append({"ticket": ticket, "gold": gold})
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
    labels = {"rule": "Rule Router", "prompt": "Prompt Router", "lora": "Router LoRA"}
    lines = [
        "# Router SFT Report",
        "",
        "| mode | json_valid | intent_acc | priority_acc | routing_acc | missing_f1 | tools_acc | human_acc |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode in ["rule", "prompt", "lora"]:
        row = summary.get(mode)
        if row is None:
            lines.append(f"| {labels[mode]} | not_run | not_run | not_run | not_run | not_run | not_run | not_run |")
            continue
        lines.append(
            f"| {labels[mode]} | {row['json_valid_rate']} | {row['intent_accuracy']} | "
            f"{row['priority_accuracy']} | {row['routing_accuracy']} | {row['missing_info_f1']} | "
            f"{row['required_tools_accuracy']} | {row['requires_human_accuracy']} |"
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
        for mode in ["rule", "prompt", "lora"]:
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
    parser.add_argument("--mode", choices=["rule", "prompt", "lora"], default="rule")
    parser.add_argument("--base_model", default=None)
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--test_file", default="data/sft_router/test.jsonl")
    parser.add_argument("--output", default="reports/router_eval_results.jsonl")
    parser.add_argument("--report", default="reports/router_sft_report.md")
    parser.add_argument("--summary-output", default="reports/router_eval_summary.jsonl")
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
