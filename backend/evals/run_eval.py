from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

from backend.agents import ServiceOpsAgent
from backend.database.models import Ticket
from backend.database.seed import seed_database
from backend.database.session import SessionLocal, init_db
from backend.evals.metrics import accuracy, mean
from backend.llm.router_model import LoraRouterModel, RouterModel
from backend.llm.verifier_model import LoraVerifierModel, VerifierModel
from backend.llm.local_lora_runtime import LocalLoRAJsonModel
from backend.rag import HybridRetriever

MODES = [
    "direct_llm",
    "rag_only",
    "agent_rule_router_prompt_verifier",
    "agent_router_lora_prompt_verifier",
    "agent_router_lora_verifier_lora",
]


def evaluate(
    dataset_path: str | Path,
    mode: str = "agent_rule_router_prompt_verifier",
    limit: int | None = None,
    output: str | Path = "reports/end_to_end_eval_results.jsonl",
    base_model: str = "Qwen/Qwen2.5-3B-Instruct",
    router_adapter: str = "outputs/router-lora-v1",
    verifier_adapter: str = "outputs/verifier-lora-v1",
    use_local_lora: bool = False,
) -> dict:
    init_db()
    db = SessionLocal()
    details = []
    failures = []
    try:
        seed_database(db)
        rows = _read_jsonl(dataset_path)
        if limit is not None:
            rows = rows[:limit]
        agent = _make_agent(mode, base_model, router_adapter, verifier_adapter, use_local_lora)
        retriever = HybridRetriever()
        router = RouterModel()

        for index, row in enumerate(rows, start=1):
            started = time.perf_counter()
            if mode == "direct_llm":
                result = _direct_llm(row, router)
            elif mode == "rag_only":
                result = _rag_only(row, router, retriever)
            else:
                result = _agent_eval(db, agent, row, index, mode)
            latency_ms = (time.perf_counter() - started) * 1000
            result["latency_ms"] = latency_ms
            detail, row_failures = _score_row(row, result, mode)
            details.append(detail)
            failures.extend(row_failures)

        metrics = _aggregate(details)
        metrics["mode"] = mode
        metrics["rows"] = len(rows)
        metrics["dataset"] = str(dataset_path)
        metrics["sample_count"] = len(rows)
        _write_reports(metrics, details, failures, dataset_path, output)
        return metrics
    finally:
        db.close()


def evaluate_all(
    dataset_path: str | Path,
    limit: int | None = None,
    output: str | Path = "reports/end_to_end_eval_results.jsonl",
    base_model: str = "Qwen/Qwen2.5-3B-Instruct",
    router_adapter: str = "outputs/router-lora-v1",
    verifier_adapter: str = "outputs/verifier-lora-v1",
    use_local_lora: bool = False,
) -> list[dict]:
    results = []
    all_details = []
    all_failures = []
    for mode in MODES:
        try:
            metrics = evaluate(
                dataset_path,
                mode=mode,
                limit=limit,
                output=output,
                base_model=base_model,
                router_adapter=router_adapter,
                verifier_adapter=verifier_adapter,
                use_local_lora=use_local_lora,
            )
            details = _read_jsonl("reports/end_to_end_eval_details.jsonl")
            failures = _read_jsonl("reports/failure_analysis_details.jsonl")
            all_details.extend(details)
            all_failures.extend(failures)
        except RuntimeError as exc:
            metrics = _unavailable_metrics(mode, dataset_path, limit, str(exc))
        results.append(metrics)
    _write_jsonl(output, results)
    lines = [
        "# End-to-End Eval",
        "",
        f"Dataset: `{dataset_path}`",
        "",
        f"Limit: `{limit if limit is not None else 'full'}`",
        "",
        "| mode | sample_count | intent | routing | priority | tool_recall | citation | human | unsupported | success | latency_ms | tool_calls | status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for metrics in results:
        row_metrics = dict(metrics)
        row_metrics["status"] = str(row_metrics.get("status", "ok")).replace("|", "/")
        lines.append(
            "| {mode} | {sample_count} | {intent_accuracy} | {routing_accuracy} | {priority_accuracy} | {required_tool_recall} | {citation_hit_rate} | {requires_human_accuracy} | {unsupported_claim_rate} | {end_to_end_success_rate} | {avg_latency_ms} | {avg_tool_calls} | {status} |".format(
                **row_metrics,
            )
        )
    lines.extend(
        [
            "",
            "Notes:",
            "",
            "- LoRA modes instantiate the adapter runtime and are marked unavailable if the base model cannot be loaded locally.",
            "- Synthetic hard eval and manual holdout eval are reported separately when both are run.",
        ]
    )
    Path("reports/end_to_end_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_jsonl("reports/end_to_end_eval_details.jsonl", all_details)
    _write_failure_report(all_failures)
    _write_lora_integration_report(base_model, router_adapter, verifier_adapter, results, use_local_lora)
    return results


def _make_agent(
    mode: str,
    base_model: str,
    router_adapter: str,
    verifier_adapter: str,
    use_local_lora: bool = False,
) -> ServiceOpsAgent:
    runtime = None
    if use_local_lora and mode in {"agent_router_lora_prompt_verifier", "agent_router_lora_verifier_lora"}:
        runtime = LocalLoRAJsonModel(
            base_model_path_or_id=base_model,
            router_adapter_path=router_adapter,
            verifier_adapter_path=verifier_adapter,
            device=os.getenv("LOCAL_LORA_DEVICE", "auto"),
            torch_dtype=os.getenv("LOCAL_LORA_TORCH_DTYPE", "auto"),
            max_new_tokens=int(os.getenv("LOCAL_LORA_MAX_NEW_TOKENS", "256")),
        )

    if mode in {"agent_router_lora_prompt_verifier", "agent_router_lora_verifier_lora"}:
        router = LoraRouterModel(
            base_model=base_model,
            adapter_path=router_adapter,
            verifier_adapter_path=verifier_adapter,
            runtime=runtime,
            use_local_runtime=use_local_lora and runtime is None,
        )
    else:
        router = RouterModel()

    if mode == "agent_router_lora_verifier_lora":
        verifier = LoraVerifierModel(
            base_model=base_model,
            adapter_path=verifier_adapter,
            router_adapter_path=router_adapter,
            runtime=runtime,
            use_local_runtime=use_local_lora and runtime is None,
        )
    else:
        verifier = VerifierModel()
    return ServiceOpsAgent(router=router, verifier=verifier)


def _direct_llm(row: dict, router: RouterModel) -> dict:
    classification = router.classify(row["ticket"])
    return {
        "classification": classification,
        "rag_doc_ids": [],
        "tool_names": [],
        "requires_human": classification.get("requires_human", False),
        "unsupported_claims": ["no_evidence_direct_answer"],
        "status": "DRAFTED",
    }


def _rag_only(row: dict, router: RouterModel, retriever: HybridRetriever) -> dict:
    classification = router.classify(row["ticket"])
    chunks = retriever.search(row["ticket"], top_k=5)
    return {
        "classification": classification,
        "rag_doc_ids": [chunk["doc_id"] for chunk in chunks],
        "tool_names": [],
        "requires_human": classification.get("requires_human", False),
        "unsupported_claims": [],
        "status": "DRAFTED_WITH_RAG",
    }


def _agent_eval(db, agent: ServiceOpsAgent, row: dict, index: int, mode: str) -> dict:
    ticket_id = f"EVAL_{mode}_{index:04d}"[:64]
    existing = db.get(Ticket, ticket_id)
    if existing:
        db.delete(existing)
        db.commit()
    ticket = Ticket(
        ticket_id=ticket_id,
        subject=f"Eval ticket {index}",
        body=row["ticket"],
        status="CREATED",
        missing_info=[],
        final_summary={},
    )
    db.add(ticket)
    db.commit()
    state = agent.run(db, ticket_id)
    return {
        "classification": state["classification"],
        "rag_doc_ids": [chunk["doc_id"] for chunk in state["rag_chunks"]],
        "tool_names": [item["tool_name"] for item in state["tool_results"]],
        "requires_human": state["verifier"]["requires_approval"],
        "unsupported_claims": state["verifier"].get("unsupported_claims", []),
        "status": state["final_status"],
        "avg_tool_calls": len(state["tool_results"]),
    }


def _score_row(row: dict, result: dict, mode: str) -> tuple[dict, list[dict]]:
    classification = result["classification"]
    expected_tools = set(row.get("expected_tools", []))
    called_tools = set(result.get("tool_names", []))
    expected_citations = set(row.get("expected_citations", row.get("expected_doc_ids", [])))
    returned_citations = set(result.get("rag_doc_ids", []))

    tool_recall = len(expected_tools & called_tools) / len(expected_tools) if expected_tools else 1.0
    citation_hit = bool(expected_citations & returned_citations) if expected_citations else True
    unsupported = bool(result.get("unsupported_claims"))
    routing_pred = classification.get("suggested_team", "").split(",")[0]
    routing_gold = row.get("expected_team") or row.get("suggested_team")

    detail = {
        "mode": mode,
        "ticket": row["ticket"],
        "expected_intent": row.get("expected_intent", row.get("intent")),
        "predicted_intent": classification.get("intent"),
        "expected_team": routing_gold,
        "predicted_team": routing_pred,
        "expected_priority": row.get("expected_priority", row.get("priority")),
        "predicted_priority": classification.get("priority"),
        "intent_ok": classification.get("intent") == row.get("expected_intent", row.get("intent")),
        "priority_ok": classification.get("priority") == row.get("expected_priority", row.get("priority")),
        "routing_ok": routing_pred == routing_gold if routing_gold else True,
        "required_tool_recall": tool_recall,
        "citation_hit": citation_hit,
        "requires_human_ok": result.get("requires_human") == row.get("requires_human"),
        "unsupported_claim": unsupported,
        "latency_ms": result["latency_ms"],
        "tool_calls": len(called_tools),
        "status": result.get("status"),
        "json_valid": classification.get("raw_json_valid", True),
    }
    detail["end_to_end_success"] = (
        detail["intent_ok"]
        and detail["priority_ok"]
        and detail["routing_ok"]
        and tool_recall >= 0.999
        and citation_hit
        and detail["requires_human_ok"]
        and not unsupported
    )

    failures = []
    if not detail["intent_ok"]:
        failures.append(_failure("classification_error", row, result, mode))
    if not detail["routing_ok"]:
        failures.append(_failure("routing_error", row, result, mode))
    if tool_recall < 0.999:
        failures.append(_failure("tool_call_error", row, result, mode))
    if not citation_hit:
        failures.append(_failure("retrieval_miss", row, result, mode))
    if unsupported:
        failures.append(_failure("unsupported_claim", row, result, mode))
    if not detail["json_valid"]:
        failures.append(_failure("json_invalid", row, result, mode))
    if result.get("requires_human") is False and row.get("requires_human") is True:
        failures.append(_failure("verifier_false_approval", row, result, mode))
    if result.get("requires_human") is True and row.get("requires_human") is False:
        failures.append(_failure("verifier_over_block", row, result, mode))
    if result["latency_ms"] > 5000:
        failures.append(_failure("latency_high", row, result, mode))
    return detail, failures


def _failure(kind: str, row: dict, result: dict, mode: str) -> dict:
    classification = result["classification"]
    return {
        "type": kind,
        "mode": mode,
        "ticket_id": row.get("ticket_id", row.get("id", "")),
        "ticket": row["ticket"][:240],
        "expected_intent": row.get("expected_intent", row.get("intent")),
        "predicted_intent": classification.get("intent"),
        "expected_team": row.get("expected_team", row.get("suggested_team")),
        "predicted_team": classification.get("suggested_team"),
        "expected_priority": row.get("expected_priority", row.get("priority")),
        "predicted_priority": classification.get("priority"),
        "expected_tools": row.get("expected_tools", []),
        "predicted_tools": result.get("tool_names", []),
        "requires_human_expected": row.get("requires_human"),
        "requires_human_predicted": result.get("requires_human"),
        "root_cause": _likely_root_cause(kind),
        "proposed_fix": _proposed_fix(kind),
    }


def _aggregate(details: list[dict]) -> dict:
    return {
        "intent_accuracy": round(mean([1.0 if item["intent_ok"] else 0.0 for item in details]), 4),
        "routing_accuracy": round(mean([1.0 if item["routing_ok"] else 0.0 for item in details]), 4),
        "priority_accuracy": round(mean([1.0 if item["priority_ok"] else 0.0 for item in details]), 4),
        "required_tool_recall": round(mean([item["required_tool_recall"] for item in details]), 4),
        "citation_hit_rate": round(mean([1.0 if item["citation_hit"] else 0.0 for item in details]), 4),
        "requires_human_accuracy": round(
            mean([1.0 if item["requires_human_ok"] else 0.0 for item in details]), 4
        ),
        "unsupported_claim_rate": round(
            mean([1.0 if item["unsupported_claim"] else 0.0 for item in details]), 4
        ),
        "end_to_end_success_rate": round(
            mean([1.0 if item["end_to_end_success"] else 0.0 for item in details]), 4
        ),
        "avg_latency_ms": round(mean([item["latency_ms"] for item in details]), 3),
        "avg_tool_calls": round(mean([item["tool_calls"] for item in details]), 3),
    }


def _write_reports(
    metrics: dict,
    details: list[dict],
    failures: list[dict],
    dataset_path: str | Path,
    output: str | Path,
) -> None:
    Path("reports").mkdir(exist_ok=True)
    _write_jsonl("reports/end_to_end_eval_details.jsonl", details)
    _write_jsonl("reports/failure_analysis_details.jsonl", failures)
    _write_jsonl(output, [metrics])
    lines = [
        "# End-to-End Eval",
        "",
        f"Dataset: `{dataset_path}`",
        "",
        f"Sample count: `{metrics['sample_count']}`",
        "",
        "| mode | sample_count | intent | routing | priority | tool_recall | citation | human | unsupported | success | latency_ms | tool_calls |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        "| {mode} | {sample_count} | {intent_accuracy} | {routing_accuracy} | {priority_accuracy} | {required_tool_recall} | {citation_hit_rate} | {requires_human_accuracy} | {unsupported_claim_rate} | {end_to_end_success_rate} | {avg_latency_ms} | {avg_tool_calls} |".format(
            **metrics
        ),
        "",
        "Target comparison modes:",
        "",
        "- direct_llm",
        "- rag_only",
        "- agent_rule_router_prompt_verifier",
        "- agent_router_lora_prompt_verifier",
        "- agent_router_lora_verifier_lora",
    ]
    Path("reports/end_to_end_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    _write_failure_report(failures)


def _write_failure_report(failures: list[dict]) -> None:
    counts = Counter(item["type"] for item in failures)
    failure_lines = ["# Failure Analysis", "", "| failure_type | count |", "| --- | ---: |"]
    for kind in [
        "classification_error",
        "routing_error",
        "missing_info_error",
        "required_tool_error",
        "retrieval_miss",
        "wrong_citation",
        "tool_call_error",
        "verifier_false_approval",
        "verifier_over_block",
        "unsupported_claim",
        "refusal_needed_but_not_refused",
        "latency_high",
        "json_invalid",
    ]:
        failure_lines.append(f"| {kind} | {counts.get(kind, 0)} |")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for failure in failures:
        grouped[failure["type"]].append(failure)
    failure_lines.append("")
    failure_lines.append("## Samples")
    for kind, items in grouped.items():
        failure_lines.append("")
        failure_lines.append(f"### {kind}")
        for item in items[:5]:
            failure_lines.append(
                f"- ticket_id={item.get('ticket_id') or 'n/a'} mode={item['mode']} "
                f"expected={item['expected_intent']} predicted={item['predicted_intent']} "
                f"root_cause={item['root_cause']} fix={item['proposed_fix']} ticket={item['ticket']}"
            )
    Path("reports/failure_analysis.md").write_text("\n".join(failure_lines) + "\n", encoding="utf-8")


def _write_lora_integration_report(
    base_model: str,
    router_adapter: str,
    verifier_adapter: str,
    results: list[dict],
    use_local_lora: bool,
) -> None:
    lines = [
        "# E2E LoRA Integration",
        "",
        "## Runtime Design",
        "",
        "- `agent_router_lora_prompt_verifier` uses `LoraRouterModel` with the Router adapter and the baseline verifier.",
        "- `agent_router_lora_verifier_lora` uses `LoraRouterModel` and `LoraVerifierModel`.",
        "- With `--use-local-lora`, the shared `LocalLoRAJsonModel` loads the base model once and switches Router/Verifier adapters when supported.",
        "- Without `--use-local-lora`, the legacy single-adapter `LoraJsonModel` path remains available for compatibility.",
        "- Generation is deterministic with `do_sample=False`, `attention_mask`, and `max_new_tokens <= 256`.",
        "- If the local machine cannot load the base model, LoRA E2E modes are marked unavailable rather than replaced with proxy metrics.",
        "",
        "## Configuration",
        "",
        f"- base_model: `{base_model}`",
        f"- router_adapter: `{router_adapter}`",
        f"- verifier_adapter: `{verifier_adapter}`",
        f"- use_local_lora: `{use_local_lora}`",
        "",
        "## Mode Status",
        "",
        "| mode | status | sample_count | success | routing | unsupported |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            f"| {result['mode']} | {result.get('status', 'ok')} | {result.get('sample_count', 0)} | "
            f"{result.get('end_to_end_success_rate', 'n/a')} | {result.get('routing_accuracy', 'n/a')} | "
            f"{result.get('unsupported_claim_rate', 'n/a')} |"
        )
    Path("reports/e2e_lora_integration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _likely_root_cause(kind: str) -> str:
    causes = {
        "classification_error": "Router confused mixed or underspecified enterprise support intent.",
        "routing_error": "Predicted team did not match taxonomy owner for the expected intent.",
        "missing_info_error": "Missing-info extraction did not align with expected required fields.",
        "required_tool_error": "Planner/tool selection omitted one or more expected tools.",
        "tool_call_error": "Tool sequence did not cover expected backend lookup.",
        "retrieval_miss": "RAG retrieval missed expected evidence document.",
        "wrong_citation": "Retrieved citation did not match expected source.",
        "verifier_false_approval": "Verifier allowed a case that should require human approval.",
        "verifier_over_block": "Verifier required approval for a low-risk case.",
        "unsupported_claim": "Draft included a claim not grounded by retrieved evidence or tool results.",
        "refusal_needed_but_not_refused": "Risky/no-answer case was not blocked or escalated.",
        "latency_high": "Evaluation exceeded latency threshold.",
        "json_invalid": "Model output was not parseable JSON.",
    }
    return causes.get(kind, "Unknown failure mode.")


def _proposed_fix(kind: str) -> str:
    fixes = {
        "classification_error": "Add manual mixed-intent examples and route ambiguous cases to follow-up.",
        "routing_error": "Tighten taxonomy labels and add team-level contrastive examples.",
        "missing_info_error": "Add required-field rules for account_id/request_id/order_id/deployment_id.",
        "required_tool_error": "Improve required-tool labels and next-action planner rules.",
        "tool_call_error": "Add tool argument validation and retry/fallback logic.",
        "retrieval_miss": "Improve metadata filters, chunk titles, and reranker coverage.",
        "wrong_citation": "Enforce citation checker before reply drafting.",
        "verifier_false_approval": "Increase negative verifier examples for sensitive actions.",
        "verifier_over_block": "Add low-risk pass examples and decision threshold calibration.",
        "unsupported_claim": "Constrain writer to retrieved evidence and tool outputs.",
        "refusal_needed_but_not_refused": "Add no-answer/refusal policy checks before approval.",
        "latency_high": "Cache retrievers/models and limit generated tokens.",
        "json_invalid": "Constrain decoding and add JSON repair/retry.",
    }
    return fixes.get(kind, "Inspect examples and add targeted eval cases.")


def _unavailable_metrics(
    mode: str,
    dataset_path: str | Path,
    limit: int | None,
    reason: str,
) -> dict:
    return {
        "intent_accuracy": "n/a",
        "routing_accuracy": "n/a",
        "priority_accuracy": "n/a",
        "required_tool_recall": "n/a",
        "citation_hit_rate": "n/a",
        "requires_human_accuracy": "n/a",
        "unsupported_claim_rate": "n/a",
        "end_to_end_success_rate": "n/a",
        "avg_latency_ms": "n/a",
        "avg_tool_calls": "n/a",
        "mode": mode,
        "rows": 0,
        "sample_count": limit or 0,
        "dataset": str(dataset_path),
        "status": f"unavailable: {reason[:180]}",
    }


def _read_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: str | Path, rows: list[dict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/eval/end_to_end_eval.jsonl")
    parser.add_argument("--mode", choices=MODES + ["all"], default="agent_rule_router_prompt_verifier")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", default="reports/end_to_end_eval_results.jsonl")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--base-model-path", default=os.getenv("LOCAL_BASE_MODEL_PATH", "models/Qwen2.5-3B-Instruct"))
    parser.add_argument("--router-adapter", default="outputs/router-lora-v1")
    parser.add_argument("--verifier-adapter", default="outputs/verifier-lora-v1")
    parser.add_argument("--use-local-lora", action="store_true")
    args = parser.parse_args()
    base_model = args.base_model_path if args.use_local_lora else args.base_model
    if args.mode == "all":
        result = evaluate_all(
            args.dataset,
            limit=args.limit,
            output=args.output,
            base_model=base_model,
            router_adapter=args.router_adapter,
            verifier_adapter=args.verifier_adapter,
            use_local_lora=args.use_local_lora,
        )
    else:
        result = evaluate(
            args.dataset,
            mode=args.mode,
            limit=args.limit,
            output=args.output,
            base_model=base_model,
            router_adapter=args.router_adapter,
            verifier_adapter=args.verifier_adapter,
            use_local_lora=args.use_local_lora,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
