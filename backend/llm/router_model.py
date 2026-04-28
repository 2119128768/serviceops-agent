from __future__ import annotations

import re

from backend.llm.local_lora_runtime import LocalLoRAJsonModel
from backend.llm.lora_json_model import LoraJsonModel


ROUTER_SYSTEM_PROMPT = "你是企业技术支持工单 Router。请只输出合法 JSON，不要输出解释。"


class RouterModel:
    """Deterministic Router baseline.

    The production swap point is a vLLM/OpenAI-compatible client or Router LoRA adapter.
    Keeping this baseline deterministic makes evaluation and local development stable.
    """

    def classify(self, text: str) -> dict:
        normalized = text.lower()

        if _contains(normalized, ["p1/p0", "平台事故", "全局故障", "多个区域", "大量客户", "503", "incident"]):
            return _output(
                "incident_outage",
                "platform",
                "P1",
                "incident_commander",
                "platform_support",
                "high",
                _missing(text, {"request_id": r"req_[A-Za-z0-9_]+"}),
                ["get_sla_policy"],
                True,
                True,
            )

        if _contains(normalized, ["隐私", "泄露", "审计", "敏感数据", "删除所有副本", "风险评分"]):
            return _output(
                "security_privacy",
                "security",
                "P1",
                "security_ops",
                "platform_support",
                "high",
                _missing(text, {"account_id": r"acc_[A-Za-z0-9_]+", "project_id": r"proj_[A-Za-z0-9_]+"}),
                ["get_customer_profile", "get_sla_policy"],
                True,
                True,
            )

        if _contains(normalized, ["permission denied", "权限", "owner", "降权", "成员列表"]):
            return _output(
                "permission_issue",
                "console",
                "P2",
                "security_ops",
                "platform_support",
                "high",
                _missing(text, {"account_id": r"acc_[A-Za-z0-9_]+", "project_id": r"proj_[A-Za-z0-9_]+"}),
                ["get_customer_profile", "get_sla_policy"],
                True,
                True,
            )

        if _contains(normalized, ["发票", "退款", "invoice", "refund", "额度没有增加", "付款", "订单", "套餐升级"]):
            return _output(
                "quota_billing",
                "billing",
                "P2",
                "billing_system",
                "platform_support",
                "high",
                _missing(text, {"account_id": r"acc_[A-Za-z0-9_]+", "order_id": r"ord_[A-Za-z0-9_]+"}),
                ["query_order_status", "get_customer_profile", "get_sla_policy"],
                True,
                True,
            )

        if _contains(normalized, ["cuda out of memory", "gpu memory", "oom", "显存不足", "out of memory"]):
            return _output(
                "gpu_memory_error",
                "model_deployment",
                "P2",
                "model_serving",
                "platform_support",
                "medium",
                _missing(text, {"deployment_id": r"dep_[A-Za-z0-9_]+"}),
                ["get_deployment_status", "get_sla_policy"],
                True,
                False,
            )

        if _contains(normalized, ["部署", "deployment", "容器", "镜像", "endpoint", "发布失败"]):
            return _output(
                "deployment_failure",
                "model_deployment",
                "P2",
                "model_serving",
                "platform_support",
                "medium",
                _missing(text, {"deployment_id": r"dep_[A-Za-z0-9_]+"}),
                ["get_deployment_status", "get_sla_policy"],
                True,
                False,
            )

        if _contains(normalized, ["导入", "parsing", "上传文档", "pending", "乱码"]):
            return _output(
                "rag_import_error",
                "knowledge_base",
                "P3",
                "knowledge_platform",
                "platform_support",
                "low",
                _missing(text, {"project_id": r"proj_[A-Za-z0-9_]+"}),
                ["get_sla_policy"],
                True,
                False,
            )

        if _contains(normalized, ["rag", "知识库", "embedding", "检索", "召回", "chunk", "metadata"]):
            return _output(
                "rag_quality_issue",
                "knowledge_base",
                "P3",
                "knowledge_platform",
                "platform_support",
                "low",
                _missing(text, {"project_id": r"proj_[A-Za-z0-9_]+"}),
                ["get_sla_policy"],
                True,
                False,
            )

        if _contains(normalized, ["延迟", "latency", "超时", "很慢", "p95", "20 秒"]):
            return _output(
                "model_latency",
                "model_api",
                "P2",
                "platform_support",
                "model_serving",
                "medium",
                _missing(text, {"request_id": r"req_[A-Za-z0-9_]+"}),
                ["check_api_status", "get_sla_policy"],
                True,
                False,
            )

        if _contains(normalized, ["rate_limited", "rate limit", "qps", "tpm", "并发", "限速", "限流"]):
            return _output(
                "api_rate_limit_error",
                "model_api",
                "P2",
                "platform_support",
                "",
                "low",
                _missing(text, {"request_id": r"req_[A-Za-z0-9_]+", "account_id": r"acc_[A-Za-z0-9_]+"}),
                ["check_api_status", "get_customer_profile", "get_sla_policy"],
                True,
                False,
            )

        if _contains(normalized, ["429", "quota", "额度", "充值", "限流", "rate limit"]):
            return _output(
                "api_quota_error",
                "model_api",
                "P2",
                "platform_support",
                "billing_system",
                "medium",
                _missing(text, {"account_id": r"acc_[A-Za-z0-9_]+", "order_id": r"ord_[A-Za-z0-9_]+"}),
                ["check_api_status", "query_order_status", "get_sla_policy"],
                True,
                True,
            )

        if _contains(normalized, ["401", "authentication", "api key", "鉴权", "认证"]):
            return _output(
                "api_auth_error",
                "model_api",
                "P2",
                "platform_support",
                "security_ops",
                "low",
                _missing(text, {"request_id": r"req_[A-Za-z0-9_]+", "project_id": r"proj_[A-Za-z0-9_]+"}),
                ["get_sla_policy"],
                True,
                False,
            )

        if _contains(normalized, ["账号", "登录", "企业空间", "被冻结", "手机号", "实名", "合并"]):
            return _output(
                "account_issue",
                "account",
                "P3",
                "customer_service",
                "platform_support",
                "medium",
                _missing(text, {"account_id": r"acc_[A-Za-z0-9_]+"}),
                ["get_customer_profile", "get_sla_policy"],
                True,
                True,
            )

        if _contains(normalized, ["希望", "建议", "feature", "roadmap", "能不能", "是否可以", "产品建议"]):
            return _output(
                "feature_request",
                "platform",
                "P3",
                "product_feedback",
                "",
                "low",
                [],
                ["get_sla_policy"],
                True,
                False,
            )

        if _contains(normalized, ["不好用了", "不确定", "稍后补", "无法调用", "没有错误", "具体错误"]):
            return _output(
                "ambiguous_missing_info",
                "unknown",
                "P3",
                "support_queue",
                "",
                "low",
                _missing(text, {"request_id": r"req_[A-Za-z0-9_]+", "account_id": r"acc_[A-Za-z0-9_]+"}),
                ["get_sla_policy"],
                True,
                False,
            )

        return _output(
            "ambiguous_missing_info",
            "unknown",
            "P3",
            "support_queue",
            "",
            "low",
            _missing(text, {"request_id": r"req_[A-Za-z0-9_]+", "account_id": r"acc_[A-Za-z0-9_]+"}),
            ["get_sla_policy"],
            True,
            False,
        )


class LoraRouterModel:
    """Router adapter wrapper used by runtime and end-to-end evaluation."""

    def __init__(
        self,
        base_model: str = "Qwen/Qwen2.5-3B-Instruct",
        adapter_path: str = "outputs/router-lora-v1",
        runtime: LocalLoRAJsonModel | None = None,
        use_local_runtime: bool = False,
        verifier_adapter_path: str = "outputs/verifier-lora-v1",
    ) -> None:
        self.runtime = runtime
        self.runner: LoraJsonModel | None = None
        if self.runtime is None and use_local_runtime:
            self.runtime = LocalLoRAJsonModel(
                base_model_path_or_id=base_model,
                router_adapter_path=adapter_path,
                verifier_adapter_path=verifier_adapter_path,
            )
        if self.runtime is None:
            self.runner = LoraJsonModel(
                base_model=base_model,
                adapter_path=adapter_path,
                system_prompt=ROUTER_SYSTEM_PROMPT,
                max_new_tokens=256,
            )

    def classify(self, text: str) -> dict:
        if self.runtime is not None:
            output = self.runtime.predict_router(text)
        else:
            if self.runner is None:
                raise RuntimeError("Router LoRA runner is not initialized.")
            output = self.runner.generate_json(f"工单：{text}")
        if not output:
            invalid = _invalid_router_output()
            invalid["raw_json_valid"] = False
            return invalid
        output.setdefault("intent", "json_invalid")
        output.setdefault("product", "unknown")
        output.setdefault("priority", "P3")
        output.setdefault("suggested_team", "support_queue")
        output.setdefault("secondary_team", "")
        output.setdefault("missing_info", [])
        output.setdefault("required_tools", [])
        output.setdefault("needs_rag", True)
        output.setdefault("requires_human", False)
        output.setdefault("risk_level", "medium" if output.get("requires_human") else "low")
        output["raw_json_valid"] = True
        return output


def _contains(text: str, needles: list[str]) -> bool:
    return any(needle.lower() in text for needle in needles)


def _missing(text: str, patterns: dict[str, str]) -> list[str]:
    return [name for name, pattern in patterns.items() if not re.search(pattern, text)]


def _output(
    intent: str,
    product: str,
    priority: str,
    suggested_team: str,
    secondary_team: str,
    risk_level: str,
    missing_info: list[str],
    required_tools: list[str],
    needs_rag: bool,
    requires_human: bool,
) -> dict:
    return {
        "intent": intent,
        "product": product,
        "priority": priority,
        "suggested_team": suggested_team,
        "secondary_team": secondary_team,
        "missing_info": missing_info,
        "required_tools": required_tools,
        "needs_rag": needs_rag,
        "requires_human": requires_human,
        "risk_level": risk_level,
    }


def _invalid_router_output() -> dict:
    return _output(
        "json_invalid",
        "unknown",
        "P3",
        "support_queue",
        "",
        "medium",
        ["request_id", "account_id"],
        ["get_sla_policy"],
        True,
        True,
    )
