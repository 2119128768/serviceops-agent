from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from data_pipeline.common import read_jsonl, split_rows, stable_shuffle, write_jsonl

SYSTEM_PROMPT = "你是企业技术支持工单 Router。请只输出合法 JSON，不要输出解释。"


def build_rows(input_path: str) -> list[dict]:
    rows = read_jsonl(input_path)
    sft_rows: list[dict] = []
    for row in rows:
        completion = {
            "intent": row["intent"],
            "product": row["product"],
            "priority": row["priority"],
            "suggested_team": row["suggested_team"],
            "secondary_team": row["secondary_team"],
            "missing_info": row["missing_info"],
            "required_tools": row["required_tools"],
            "needs_rag": row["needs_rag"],
            "requires_human": row["requires_human"],
            "risk_level": row["risk_level"],
        }
        sft_rows.append(
            {
                "prompt": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"工单：{row['text']}"},
                ],
                "completion": [
                    {
                        "role": "assistant",
                        "content": json.dumps(completion, ensure_ascii=False, separators=(",", ":")),
                    }
                ],
                "metadata": {
                    "ticket_id": row["ticket_id"],
                    "intent": row["intent"],
                    "priority": row["priority"],
                    "difficulty": row["difficulty"],
                    "case_type": row["case_type"],
                    "risk_level": row["risk_level"],
                    "requires_human": row["requires_human"],
                },
            }
        )
    return sft_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/synthetic_tickets/ai_platform_tickets.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-output", default="data/sft_router/train.jsonl")
    parser.add_argument("--val-output", default="data/sft_router/val.jsonl")
    parser.add_argument("--test-output", default="data/sft_router/test.jsonl")
    args = parser.parse_args()

    rows = stable_shuffle(build_rows(args.input), args.seed)
    train, val, test = split_rows(rows)
    write_jsonl(args.train_output, train)
    write_jsonl(args.val_output, val)
    write_jsonl(args.test_output, test)
    print(f"router_sft train={len(train)} val={len(val)} test={len(test)}")


if __name__ == "__main__":
    main()
