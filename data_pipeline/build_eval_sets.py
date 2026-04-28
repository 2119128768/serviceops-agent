from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from data_pipeline.common import read_jsonl, stable_shuffle, write_jsonl


def build_router(rows: list[dict], limit: int) -> list[dict]:
    selected = _hard_first(rows, limit)
    return [
        {
            "ticket": row["text"],
            "intent": row["intent"],
            "priority": row["priority"],
            "suggested_team": row["suggested_team"],
            "secondary_team": row["secondary_team"],
            "missing_info": row["missing_info"],
            "required_tools": row["required_tools"],
            "requires_human": row["requires_human"],
            "risk_level": row["risk_level"],
        }
        for row in selected
    ]


def build_rag(rows: list[dict], limit: int) -> list[dict]:
    selected = _hard_first(rows, limit)
    output = []
    for row in selected:
        output.append(
            {
                "query": row["text"],
                "expected_doc_ids": row["expected_citations"],
                "expected_citation_ids": row["expected_citations"],
                "intent": row["intent"],
                "difficulty": row["difficulty"],
            }
        )
    return output


def build_e2e(rows: list[dict], limit: int) -> list[dict]:
    selected = _hard_first(rows, limit)
    output = []
    for row in selected:
        output.append(
            {
                "ticket": row["text"],
                "expected_intent": row["intent"],
                "expected_priority": row["priority"],
                "expected_team": row["suggested_team"],
                "expected_secondary_team": row["secondary_team"],
                "expected_tools": _callable_tools(row),
                "expected_citations": row["expected_citations"],
                "requires_human": row["requires_human"],
                "expected_status": row["expected_status"],
                "difficulty": row["difficulty"],
                "case_type": row["case_type"],
            }
        )
    return output


def _hard_first(rows: list[dict], limit: int) -> list[dict]:
    hard = [row for row in rows if row["difficulty"] == "hard"]
    medium = [row for row in rows if row["difficulty"] == "medium"]
    easy = [row for row in rows if row["difficulty"] == "easy"]
    selected = hard[: int(limit * 0.7)]
    selected.extend(medium[: max(limit - len(selected), 0)])
    selected.extend(easy[: max(limit - len(selected), 0)])
    return selected[:limit]


def _callable_tools(row: dict) -> list[str]:
    text = row["text"]
    tools = []
    for tool in row["required_tools"]:
        if tool == "check_api_status" and "req_" not in text:
            continue
        if tool == "query_order_status" and "ord_" not in text and "acc_" not in text:
            continue
        if tool == "get_customer_profile" and "acc_" not in text:
            continue
        if tool == "get_deployment_status" and "dep_" not in text:
            continue
        tools.append(tool)
    if "get_sla_policy" not in tools:
        tools.append("get_sla_policy")
    return tools


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/synthetic_tickets/ai_platform_tickets.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--router-limit", type=int, default=200)
    parser.add_argument("--rag-limit", type=int, default=100)
    parser.add_argument("--e2e-limit", type=int, default=150)
    args = parser.parse_args()

    rows = stable_shuffle(read_jsonl(args.input), args.seed)
    router = build_router(rows, args.router_limit)
    rag = build_rag(rows, args.rag_limit)
    e2e = build_e2e(rows, args.e2e_limit)
    write_jsonl("data/eval/router_eval_hard.jsonl", router)
    write_jsonl("data/eval/rag_eval_hard.jsonl", rag)
    write_jsonl("data/eval/end_to_end_eval_hard.jsonl", e2e)
    print(f"hard_eval router={len(router)} rag={len(rag)} e2e={len(e2e)}")


if __name__ == "__main__":
    main()
