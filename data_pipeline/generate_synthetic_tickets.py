from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from data_pipeline.common import dynamic_missing_info, load_taxonomy, write_jsonl

FILLERS = [
    "客户说生产环境受影响，希望今天内给出处理方向。",
    "控制台截图暂时没有，只有这段报错信息。",
    "这个问题已经重复出现两次，需要给内部处理建议。",
    "业务方比较着急，但我们不希望没有证据就承诺结果。",
    "请同时给出用户回复草稿和内部排查步骤。",
    "如果涉及账号或订单，请走审批流程。",
]

MIXED_ISSUES = [
    "另外他们也提到知识库检索质量变差。",
    "同时最近部署服务也有一次失败。",
    "客户还问是不是可以直接提高额度。",
    "还有人担心这会不会涉及隐私数据。",
    "他们把限流、额度和延迟混在一起描述。",
]


def generate(num: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    taxonomy = load_taxonomy()
    intents = list(taxonomy["intents"].items())
    rows: list[dict] = []

    hard_target = int(num * 0.38)
    hard_indices = set(rng.sample(range(num), hard_target))

    for index in range(num):
        intent, spec = intents[index % len(intents)]
        template = spec["text_templates"][(index // len(intents)) % len(spec["text_templates"])]
        difficulty = _difficulty(index, hard_indices, rng)
        case_type = _case_type(intent, difficulty, rng)
        identifiers = _identifiers(index, rng)
        text = template.format(**identifiers)
        text = _mutate_text(text, case_type, rng)
        text = _drop_identifier_for_missing_case(text, case_type, rng)

        missing_info = dynamic_missing_info(text, list(spec.get("missing_info", [])))
        required_tools = list(spec.get("required_tools", []))
        suggested_team = spec["default_team"]
        secondary_team = spec.get("secondary_team") or ""

        row = {
            "ticket_id": f"SYN_{seed}_{index + 1:05d}",
            "text": text,
            "intent": intent,
            "product": spec["product"],
            "priority": spec["default_priority"],
            "suggested_team": suggested_team,
            "secondary_team": secondary_team,
            "missing_info": missing_info,
            "required_tools": required_tools,
            "needs_rag": bool(spec["needs_rag"]),
            "requires_human": bool(spec["requires_human"]),
            "risk_level": spec["risk_level"],
            "expected_citations": list(spec["expected_citations"]),
            "expected_status": spec["expected_status"],
            "difficulty": difficulty,
            "case_type": case_type,
        }
        rows.append(row)

    rng.shuffle(rows)
    return rows


def _difficulty(index: int, hard_indices: set[int], rng: random.Random) -> str:
    if index in hard_indices:
        return "hard"
    return "medium" if rng.random() < 0.42 else "easy"


def _case_type(intent: str, difficulty: str, rng: random.Random) -> str:
    if difficulty == "easy":
        return "standard"
    if difficulty == "medium":
        return rng.choice(["standard", "missing_info", "ambiguous"])
    if intent in {"security_privacy", "permission_issue", "quota_billing", "api_quota_error"}:
        return rng.choice(["security_sensitive", "mixed_intent", "conclusion_without_required_info", "missing_info"])
    return rng.choice(["mixed_intent", "missing_info", "no_answer", "ambiguous"])


def _identifiers(index: int, rng: random.Random) -> dict[str, str]:
    day = 20260401 + (index % 27)
    suffix = 1000 + index
    deployment_slug = rng.choice(["gpu_001", "api_002", "rag_003", "serving_004"])
    return {
        "request_id": f"req_{day}_{suffix}",
        "account_id": f"acc_{(index % 60) + 1:04d}",
        "order_id": f"ord_{day}_{suffix}",
        "deployment_id": f"dep_{deployment_slug}",
        "project_id": f"proj_{(index % 80) + 1:04d}",
    }


def _mutate_text(text: str, case_type: str, rng: random.Random) -> str:
    if case_type == "standard":
        return text
    if case_type == "missing_info":
        return text + " " + rng.choice(["关键信息稍后补。", "现在只知道现象，ID 暂时没有。"])
    if case_type == "mixed_intent":
        return text + " " + rng.choice(MIXED_ISSUES)
    if case_type == "security_sensitive":
        return text + " 客户要求我们直接查看账号、订单或日志明细，请确认是否需要审批。"
    if case_type == "no_answer":
        return text + " 目前没有足够证据，请不要直接承诺修复或退款。"
    if case_type == "ambiguous":
        return rng.choice(["这个问题描述比较乱：", "客户原话比较口语：", "只收到一句反馈："]) + text
    if case_type == "conclusion_without_required_info":
        return text + " 客户希望我们直接确认已经支付成功并立即恢复额度。"
    return text


def _drop_identifier_for_missing_case(text: str, case_type: str, rng: random.Random) -> str:
    if case_type not in {"missing_info", "ambiguous", "no_answer"}:
        return text
    replacements = [
        ("request_id: req_", "request_id 暂无：req_"),
        ("账号 acc_", "账号暂未提供 acc_"),
        ("订单 ord_", "订单暂未提供 ord_"),
        ("部署 dep_", "部署暂未提供 dep_"),
        ("项目 proj_", "项目暂未提供 proj_"),
    ]
    mutated = text
    if rng.random() < 0.65:
        for left, right in replacements:
            mutated = mutated.replace(left, right)
    if rng.random() < 0.25:
        mutated = mutated.replace("request_id:", "请求编号缺失：")
    if rng.random() < 0.55:
        mutated = mutated.replace("req_", "请求号_")
        mutated = mutated.replace("acc_", "账号_")
        mutated = mutated.replace("ord_", "订单_")
        mutated = mutated.replace("dep_", "部署_")
        mutated = mutated.replace("proj_", "项目_")
    return mutated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/synthetic_tickets/ai_platform_tickets.jsonl")
    args = parser.parse_args()
    rows = generate(args.num, args.seed)
    write_jsonl(Path(args.output), rows)
    hard_ratio = sum(1 for row in rows if row["difficulty"] == "hard") / max(len(rows), 1)
    print(f"wrote {len(rows)} rows to {args.output}; hard_ratio={hard_ratio:.3f}")


if __name__ == "__main__":
    main()
