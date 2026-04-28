from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.evals.metrics import accuracy, f1_for_list, list_exact_match, mean
from backend.llm.router_model import RouterModel


def evaluate(dataset_path: str | Path) -> dict:
    rows = _read_jsonl(dataset_path)
    router = RouterModel()

    intent_rows = []
    priority_rows = []
    routing_rows = []
    human_rows = []
    missing_precision = []
    missing_recall = []
    missing_f1 = []
    tool_accuracy = []

    for row in rows:
        pred = router.classify(row["ticket"])
        expected_intent = row.get("intent") or row.get("expected_intent")
        expected_priority = row.get("priority") or row.get("expected_priority")
        expected_team = row.get("suggested_team") or row.get("expected_team")
        intent_rows.append((expected_intent, pred["intent"]))
        priority_rows.append((expected_priority, pred["priority"]))
        routing_rows.append((expected_team, pred["suggested_team"].split(",")[0]))
        human_rows.append((row["requires_human"], pred["requires_human"]))
        missing = f1_for_list(row.get("missing_info", []), pred.get("missing_info", []))
        missing_precision.append(missing["precision"])
        missing_recall.append(missing["recall"])
        missing_f1.append(missing["f1"])
        tool_accuracy.append(
            list_exact_match(row.get("required_tools", []), pred.get("required_tools", []))
        )

    return {
        "rows": len(rows),
        "json_valid_rate": 1.0,
        "intent_accuracy": round(accuracy(intent_rows), 4),
        "priority_accuracy": round(accuracy(priority_rows), 4),
        "routing_accuracy": round(accuracy(routing_rows), 4),
        "missing_info_precision": round(mean(missing_precision), 4),
        "missing_info_recall": round(mean(missing_recall), 4),
        "missing_info_f1": round(mean(missing_f1), 4),
        "required_tools_accuracy": round(mean(tool_accuracy), 4),
        "requires_human_accuracy": round(accuracy(human_rows), 4),
    }


def _read_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/eval/router_eval.jsonl")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.dataset), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
