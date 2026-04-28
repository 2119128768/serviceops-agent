from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from data_pipeline.common import read_jsonl, split_rows, stable_shuffle, write_jsonl

SYSTEM_PROMPT = "你是企业 Agent 回复风险 Verifier。请只输出合法 JSON，不要输出解释。"

NEGATIVE_TYPES = [
    "unsupported_claim",
    "overpromise",
    "sensitive_action_without_approval",
    "missing_citation",
    "wrong_citation",
    "conclusion_without_required_info",
]


def build_examples(input_path: str, seed: int, target_count: int) -> list[dict]:
    source = read_jsonl(input_path)
    rng = random.Random(seed)
    rows: list[dict] = []
    index = 0
    while len(rows) < target_count:
        ticket = source[index % len(source)]
        is_positive = len(rows) % 2 == 0
        if is_positive:
            rows.append(_positive(ticket))
        else:
            rows.append(_negative(ticket, NEGATIVE_TYPES[(len(rows) // 2) % len(NEGATIVE_TYPES)], rng))
        index += 1
    return rows


def _positive(ticket: dict) -> dict:
    evidence = _evidence(ticket)
    draft = (
        f"您好，我们已按 {ticket['intent']} 分类处理。当前仍需补充："
        f"{'、'.join(ticket['missing_info']) if ticket['missing_info'] else '无'}。"
        f"建议根据引用文档和工具结果继续排查，不会在缺少证据时承诺退款、改额度或关闭工单。"
        f"引用：{ticket['expected_citations'][0]}。"
    )
    output = {
        "supported_by_evidence": True,
        "unsupported_claims": [],
        "citation_errors": [],
        "contains_sensitive_action": ticket["requires_human"],
        "requires_approval": ticket["requires_human"],
        "risk_level": ticket["risk_level"],
        "decision": "request_human_approval" if ticket["requires_human"] else "pass",
    }
    return _sft(ticket, evidence, draft, output, "positive")


def _negative(ticket: dict, negative_type: str, rng: random.Random) -> dict:
    evidence = _evidence(ticket)
    unsupported: list[str] = []
    citation_errors: list[str] = []
    contains_sensitive = ticket["requires_human"]
    requires_approval = True
    risk = "high" if ticket["risk_level"] in {"medium", "high"} else "medium"

    if negative_type == "unsupported_claim":
        draft = "我们已经确认根因并完成修复，您可以立即恢复生产调用。引用：" + ticket["expected_citations"][0]
        unsupported = ["已经确认根因", "已经完成修复"]
    elif negative_type == "overpromise":
        draft = "我们承诺今天内彻底解决，并会赔付所有损失。引用：" + ticket["expected_citations"][0]
        unsupported = ["承诺今天内彻底解决", "赔付所有损失"]
    elif negative_type == "sensitive_action_without_approval":
        draft = "我们将直接查看账号、订单和日志明细，并为您修改额度。引用：" + ticket["expected_citations"][0]
        unsupported = ["直接修改额度"]
        contains_sensitive = True
    elif negative_type == "missing_citation":
        draft = "这个问题按 SOP 处理即可，但回复里没有给出任何引用来源。"
        citation_errors = ["missing_citation"]
    elif negative_type == "wrong_citation":
        wrong = rng.choice(["deployment_gpu_memory", "rag_retrieval_quality", "api_rate_limit"])
        draft = f"该结论来自不相关文档。引用：{wrong}。"
        citation_errors = [wrong]
    else:
        draft = "虽然缺少 request_id/account_id/order_id，但可以确认订单支付成功并立即恢复额度。"
        unsupported = ["缺少必要信息仍下结论", "确认订单支付成功", "立即恢复额度"]

    output = {
        "supported_by_evidence": False,
        "unsupported_claims": unsupported,
        "citation_errors": citation_errors,
        "contains_sensitive_action": contains_sensitive,
        "requires_approval": requires_approval,
        "risk_level": risk,
        "decision": "revise_before_reply",
    }
    return _sft(ticket, evidence, draft, output, negative_type)


def _evidence(ticket: dict) -> str:
    tools = ", ".join(ticket["required_tools"])
    citations = ", ".join(ticket["expected_citations"])
    return (
        f"工单分类为 {ticket['intent']}，优先级 {ticket['priority']}。"
        f"需调用工具：{tools}。"
        f"期望引用：{citations}。"
        f"缺失信息：{ticket['missing_info']}。"
        f"是否需要人工审批：{ticket['requires_human']}。"
    )


def _sft(ticket: dict, evidence: str, draft: str, output: dict, sample_type: str) -> dict:
    user = f"工单：{ticket['text']}\n证据：{evidence}\n回复草稿：{draft}"
    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "completion": [
            {
                "role": "assistant",
                "content": json.dumps(output, ensure_ascii=False, separators=(",", ":")),
            }
        ],
        "metadata": {
            "ticket_id": ticket["ticket_id"],
            "intent": ticket["intent"],
            "sample_type": sample_type,
            "requires_human": ticket["requires_human"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/synthetic_tickets/ai_platform_tickets.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num", type=int, default=1000)
    parser.add_argument("--train-output", default="data/sft_verifier/train.jsonl")
    parser.add_argument("--val-output", default="data/sft_verifier/val.jsonl")
    parser.add_argument("--test-output", default="data/sft_verifier/test.jsonl")
    args = parser.parse_args()

    rows = stable_shuffle(build_examples(args.input, args.seed, max(args.num, 1000)), args.seed)
    train, val, test = split_rows(rows, train_size=800, val_size=100, test_size=100)
    write_jsonl(args.train_output, train)
    write_jsonl(args.val_output, val)
    write_jsonl(args.test_output, test)
    print(f"verifier_sft train={len(train)} val={len(val)} test={len(test)}")


if __name__ == "__main__":
    main()
