from __future__ import annotations

import json

from backend.llm.local_lora_runtime import LocalLoRAJsonModel
from backend.llm.lora_json_model import LoraJsonModel
from backend.rag.citation_checker import CitationChecker

VERIFIER_SYSTEM_PROMPT = "你是企业 Agent 回复风险 Verifier。请只输出合法 JSON，不要输出解释。"


class VerifierModel:
    """Risk and evidence verifier baseline.

    This mirrors the intended Verifier LoRA output schema, making it straightforward to
    compare baseline vs adapter later.
    """

    def __init__(self) -> None:
        self.citation_checker = CitationChecker()

    def verify(
        self,
        ticket_text: str,
        draft_reply: str,
        evidence_chunks: list[dict],
        tool_results: list[dict],
        router_output: dict,
        plan: dict,
    ) -> dict:
        unsupported_claims = self._unsupported_claims(draft_reply, tool_results)
        sensitive_action = self._contains_sensitive_action(draft_reply, router_output, plan, tool_results)
        citation = self.citation_checker.check(draft_reply, evidence_chunks)

        risk_level = "low"
        if sensitive_action:
            risk_level = "medium"
        if any(keyword in draft_reply for keyword in ["修改额度", "退款", "关闭工单", "立即恢复额度"]):
            risk_level = "high"

        requires_approval = bool(
            router_output.get("requires_human") or sensitive_action or unsupported_claims
        )

        if unsupported_claims:
            decision = "revise_before_reply"
        elif requires_approval:
            decision = "request_human_approval"
        else:
            decision = "pass"

        return {
            "supported_by_evidence": bool(citation["has_citations"] and not unsupported_claims),
            "unsupported_claims": unsupported_claims,
            "citation_errors": citation["weak_citations"],
            "contains_sensitive_action": sensitive_action,
            "requires_approval": requires_approval,
            "risk_level": risk_level,
            "decision": decision,
            "citation_check": citation,
        }

    def _unsupported_claims(self, draft_reply: str, tool_results: list[dict]) -> list[str]:
        claims: list[str] = []
        order_results = [
            item["result"]
            for item in tool_results
            if item.get("tool_name") == "query_order_status" and item.get("result", {}).get("found")
        ]
        has_paid = any(item.get("payment_status") == "paid" for item in order_results)
        has_synced = any(item.get("quota_sync_status") == "synced" for item in order_results)

        if "订单支付成功" in draft_reply and not has_paid:
            claims.append("已经确认订单支付成功")
        if "额度已恢复" in draft_reply and not has_synced:
            claims.append("额度已恢复")
        if "立即恢复额度" in draft_reply:
            claims.append("立即恢复额度")
        return claims

    def _contains_sensitive_action(
        self, draft_reply: str, router_output: dict, plan: dict, tool_results: list[dict]
    ) -> bool:
        sensitive_words = ["额度", "订单", "账户", "账号", "退款", "发票", "审批"]
        touched_sensitive_tools = any(
            item.get("tool_name") in {"get_customer_profile", "query_order_status"}
            for item in tool_results
        )
        plan_actions = " ".join(plan.get("steps", []))
        return (
            touched_sensitive_tools
            or router_output.get("requires_human", False)
            or any(word in draft_reply or word in plan_actions for word in sensitive_words)
        )


class LoraVerifierModel:
    """Verifier adapter wrapper used by runtime and end-to-end evaluation."""

    def __init__(
        self,
        base_model: str = "Qwen/Qwen2.5-3B-Instruct",
        adapter_path: str = "outputs/verifier-lora-v1",
        runtime: LocalLoRAJsonModel | None = None,
        use_local_runtime: bool = False,
        router_adapter_path: str = "outputs/router-lora-v1",
    ) -> None:
        self.runtime = runtime
        self.runner: LoraJsonModel | None = None
        if self.runtime is None and use_local_runtime:
            self.runtime = LocalLoRAJsonModel(
                base_model_path_or_id=base_model,
                router_adapter_path=router_adapter_path,
                verifier_adapter_path=adapter_path,
            )
        if self.runtime is None:
            self.runner = LoraJsonModel(
                base_model=base_model,
                adapter_path=adapter_path,
                system_prompt=VERIFIER_SYSTEM_PROMPT,
                max_new_tokens=256,
            )

    def verify(
        self,
        ticket_text: str,
        draft_reply: str,
        evidence_chunks: list[dict],
        tool_results: list[dict],
        router_output: dict,
        plan: dict,
    ) -> dict:
        prompt = build_verifier_prompt(
            ticket_text=ticket_text,
            draft_reply=draft_reply,
            evidence_chunks=evidence_chunks,
            tool_results=tool_results,
            router_output=router_output,
            plan=plan,
        )
        if self.runtime is not None:
            output = self.runtime.predict_verifier(prompt)
        else:
            if self.runner is None:
                raise RuntimeError("Verifier LoRA runner is not initialized.")
            output = self.runner.generate_json(prompt)
        if not output:
            invalid = _invalid_verifier_output()
            invalid["raw_json_valid"] = False
            return invalid
        output.setdefault("supported_by_evidence", False)
        output.setdefault("unsupported_claims", [])
        output.setdefault("citation_errors", [])
        output.setdefault("contains_sensitive_action", False)
        output.setdefault("requires_approval", True)
        output.setdefault("risk_level", "medium")
        output.setdefault("decision", "revise_before_reply")
        output["raw_json_valid"] = True
        return output


def build_verifier_prompt(
    ticket_text: str,
    draft_reply: str,
    evidence_chunks: list[dict],
    tool_results: list[dict],
    router_output: dict,
    plan: dict,
) -> str:
    evidence = [
        {
            "doc_id": chunk.get("doc_id"),
            "chunk_id": chunk.get("chunk_id"),
            "title": chunk.get("title"),
            "content": chunk.get("content", "")[:500],
        }
        for chunk in evidence_chunks[:5]
    ]
    tools = [
        {
            "tool_name": item.get("tool_name"),
            "arguments": item.get("arguments", {}),
            "result": item.get("result", {}),
            "success": item.get("success", True),
        }
        for item in tool_results[:8]
    ]
    payload = {
        "ticket": ticket_text,
        "router_output": router_output,
        "plan": plan,
        "evidence": evidence,
        "tool_results": tools,
        "draft_reply": draft_reply,
    }
    return (
        "请检查以下企业工单回复是否被证据支持、是否有错误引用、是否包含敏感动作、是否需要人工审批。\n"
        "只输出 JSON。\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )


def _invalid_verifier_output() -> dict:
    return {
        "supported_by_evidence": False,
        "unsupported_claims": ["json_invalid"],
        "citation_errors": ["json_invalid"],
        "contains_sensitive_action": True,
        "requires_approval": True,
        "risk_level": "high",
        "decision": "revise_before_reply",
    }
