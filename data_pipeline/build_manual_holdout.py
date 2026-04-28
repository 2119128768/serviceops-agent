from __future__ import annotations

import json
from pathlib import Path


ROUTER_CASES = [
    ("MH_R_001", "客户说模型接口又慢又偶尔 429，昨天刚充值，只有 request_id: req_manual_001。", "api_quota_error", "model_api", "P2", "platform_support", "billing_system", ["account_id", "order_id"], ["check_api_status", "query_order_status", "get_sla_policy"], True, True, "medium", "mixed_intent"),
    ("MH_R_002", "报错 quota exceeded，但财务说订单已经付了，订单号 ord_manual_002，账号没找到。", "api_quota_error", "model_api", "P2", "platform_support", "billing_system", ["account_id"], ["check_api_status", "query_order_status", "get_sla_policy"], True, True, "medium", "missing_info"),
    ("MH_R_003", "线上突然大量 429，像余额不足，也可能是并发打满，acc_manual_003。", "api_rate_limit_error", "model_api", "P2", "platform_support", "", ["request_id"], ["check_api_status", "get_customer_profile", "get_sla_policy"], True, False, "low", "mixed_intent"),
    ("MH_R_004", "QPS 一到 50 就失败，控制台提示 rate limited，request_id 是 req_manual_004。", "api_rate_limit_error", "model_api", "P2", "platform_support", "", ["account_id"], ["check_api_status", "get_customer_profile", "get_sla_policy"], True, False, "low", "standard"),
    ("MH_R_005", "API key 明明没改，今天开始 401，proj_manual_005。", "api_auth_error", "model_api", "P2", "platform_support", "security_ops", ["request_id"], ["get_sla_policy"], True, False, "low", "standard"),
    ("MH_R_006", "鉴权失败，像是 token 过期，但客户只发了截图没给 project。", "api_auth_error", "model_api", "P2", "platform_support", "security_ops", ["request_id", "project_id"], ["get_sla_policy"], True, False, "low", "missing_info"),
    ("MH_R_007", "企业空间成员突然没有 owner 权限，acc_manual_007，怀疑被误降权。", "permission_issue", "console", "P2", "security_ops", "platform_support", ["project_id"], ["get_customer_profile", "get_sla_policy"], True, True, "high", "security_sensitive"),
    ("MH_R_008", "控制台 permission denied，但用户说充值页面也打不开，先看权限还是计费？", "permission_issue", "console", "P2", "security_ops", "platform_support", ["account_id", "project_id"], ["get_customer_profile", "get_sla_policy"], True, True, "high", "mixed_intent"),
    ("MH_R_009", "套餐升级后额度没变，订单 ord_manual_009 已扣款，acc_manual_009。", "quota_billing", "billing", "P2", "billing_system", "platform_support", [], ["query_order_status", "get_customer_profile", "get_sla_policy"], True, True, "high", "standard"),
    ("MH_R_010", "用户要求直接退款并补偿，只有公司名没有 account_id/order_id。", "quota_billing", "billing", "P2", "billing_system", "platform_support", ["account_id", "order_id"], ["query_order_status", "get_customer_profile", "get_sla_policy"], True, True, "high", "security_sensitive"),
    ("MH_R_011", "知识库导入卡在 pending，文件名带中文括号，proj_manual_011。", "rag_import_error", "knowledge_base", "P3", "knowledge_platform", "platform_support", [], ["get_sla_policy"], True, False, "low", "standard"),
    ("MH_R_012", "上传 PDF 后乱码，用户说点导入没反应，也没有任务 ID。", "rag_import_error", "knowledge_base", "P3", "knowledge_platform", "platform_support", ["project_id"], ["get_sla_policy"], True, False, "low", "missing_info"),
    ("MH_R_013", "RAG 总召回旧文档，metadata 明明有 version=new，proj_manual_013。", "rag_quality_issue", "knowledge_base", "P3", "knowledge_platform", "platform_support", [], ["get_sla_policy"], True, False, "low", "standard"),
    ("MH_R_014", "知识库能导入但答案胡说，像 chunk 切得不对，项目 ID 没带。", "rag_quality_issue", "knowledge_base", "P3", "knowledge_platform", "platform_support", ["project_id"], ["get_sla_policy"], True, False, "low", "ambiguous"),
    ("MH_R_015", "p95 延迟从 800ms 涨到 18 秒，request_id: req_manual_015。", "model_latency", "model_api", "P2", "platform_support", "model_serving", [], ["check_api_status", "get_sla_policy"], True, False, "medium", "standard"),
    ("MH_R_016", "接口慢到超时，客户只说今天下午开始，没给 request_id。", "model_latency", "model_api", "P2", "platform_support", "model_serving", ["request_id"], ["check_api_status", "get_sla_policy"], True, False, "medium", "missing_info"),
    ("MH_R_017", "dep_manual_017 发布后健康检查一直失败，容器日志为空。", "deployment_failure", "model_deployment", "P2", "model_serving", "platform_support", [], ["get_deployment_status", "get_sla_policy"], True, False, "medium", "standard"),
    ("MH_R_018", "模型 endpoint 刚发布就 502，镜像拉取失败，deployment_id 没贴。", "deployment_failure", "model_deployment", "P2", "model_serving", "platform_support", ["deployment_id"], ["get_deployment_status", "get_sla_policy"], True, False, "medium", "missing_info"),
    ("MH_R_019", "部署大模型时报 CUDA out of memory，dep_manual_019，用的是 24G 卡。", "gpu_memory_error", "model_deployment", "P2", "model_serving", "platform_support", [], ["get_deployment_status", "get_sla_policy"], True, False, "medium", "standard"),
    ("MH_R_020", "显存爆了但客户说昨天还能跑，同一模型同一参数，没有 deployment_id。", "gpu_memory_error", "model_deployment", "P2", "model_serving", "platform_support", ["deployment_id"], ["get_deployment_status", "get_sla_policy"], True, False, "medium", "ambiguous"),
    ("MH_R_021", "客户要求导出某账号所有调用日志和输入内容，acc_manual_021。", "security_privacy", "security", "P1", "security_ops", "platform_support", ["project_id"], ["get_customer_profile", "get_sla_policy"], True, True, "high", "security_sensitive"),
    ("MH_R_022", "怀疑数据泄露，请删除所有副本并确认没有员工看过。", "security_privacy", "security", "P1", "security_ops", "platform_support", ["account_id", "project_id"], ["get_customer_profile", "get_sla_policy"], True, True, "high", "security_sensitive"),
    ("MH_R_023", "账号被冻结，控制台只显示 contact support，acc_manual_023。", "account_issue", "account", "P3", "customer_service", "platform_support", [], ["get_customer_profile", "get_sla_policy"], True, True, "medium", "standard"),
    ("MH_R_024", "登录不上，手机号换了，企业空间也找不到，账号 ID 不知道。", "account_issue", "account", "P3", "customer_service", "platform_support", ["account_id"], ["get_customer_profile", "get_sla_policy"], True, True, "medium", "missing_info"),
    ("MH_R_025", "希望控制台支持按项目导出 token 用量，问有没有 roadmap。", "feature_request", "platform", "P3", "product_feedback", "", [], ["get_sla_policy"], True, False, "low", "standard"),
    ("MH_R_026", "能不能加一个审批流模板，客户说不是故障只是建议。", "feature_request", "platform", "P3", "product_feedback", "", [], ["get_sla_policy"], True, False, "low", "standard"),
    ("MH_R_027", "多个区域 API 503，十几个客户同时报警，没有单个 request_id。", "incident_outage", "platform", "P1", "incident_commander", "platform_support", ["request_id"], ["get_sla_policy"], True, True, "high", "no_answer"),
    ("MH_R_028", "生产全量失败，疑似平台事故，客户要求立即赔付。", "incident_outage", "platform", "P1", "incident_commander", "platform_support", ["request_id"], ["get_sla_policy"], True, True, "high", "security_sensitive"),
    ("MH_R_029", "不好用了，后台也红了，但不知道是 API、RAG 还是部署。", "ambiguous_missing_info", "unknown", "P3", "support_queue", "", ["request_id", "account_id"], ["get_sla_policy"], True, False, "low", "ambiguous"),
    ("MH_R_030", "客户说全部都坏了，截图看不清，只有一句帮忙看看。", "ambiguous_missing_info", "unknown", "P3", "support_queue", "", ["request_id", "account_id"], ["get_sla_policy"], True, False, "low", "ambiguous"),
    ("MH_R_031", "429 + 发票 + 权限三个问题混在一个工单里，先不要直接操作账号。", "api_quota_error", "model_api", "P2", "platform_support", "billing_system", ["account_id", "order_id"], ["check_api_status", "query_order_status", "get_sla_policy"], True, True, "medium", "mixed_intent"),
    ("MH_R_032", "rate limit 写成了 rtae lmti，用户说并发上去就炸，req_manual_032。", "api_rate_limit_error", "model_api", "P2", "platform_support", "", ["account_id"], ["check_api_status", "get_customer_profile", "get_sla_policy"], True, False, "low", "noisy"),
    ("MH_R_033", "ak 似乎失效了，401 unauth，项目 proj_manual_033，别让用户贴完整 key。", "api_auth_error", "model_api", "P2", "platform_support", "security_ops", ["request_id"], ["get_sla_policy"], True, False, "low", "security_sensitive"),
    ("MH_R_034", "成员被踢出项目，还要求查看另一个同事的调用记录。", "permission_issue", "console", "P2", "security_ops", "platform_support", ["account_id", "project_id"], ["get_customer_profile", "get_sla_policy"], True, True, "high", "security_sensitive"),
    ("MH_R_035", "订单显示 paid 但额度还是 0，acc_manual_035 ord_manual_035。", "quota_billing", "billing", "P2", "billing_system", "platform_support", [], ["query_order_status", "get_customer_profile", "get_sla_policy"], True, True, "high", "standard"),
    ("MH_R_036", "导入任务失败后一直重试，用户只发了 kb 名称，没有项目 ID。", "rag_import_error", "knowledge_base", "P3", "knowledge_platform", "platform_support", ["project_id"], ["get_sla_policy"], True, False, "low", "missing_info"),
    ("MH_R_037", "检索结果引用了旧 SOP，客户怀疑 metadata filter 没生效。", "rag_quality_issue", "knowledge_base", "P3", "knowledge_platform", "platform_support", ["project_id"], ["get_sla_policy"], True, False, "low", "standard"),
    ("MH_R_038", "流式输出首 token 很慢，request_id req_manual_038，客户生产受影响。", "model_latency", "model_api", "P2", "platform_support", "model_serving", [], ["check_api_status", "get_sla_policy"], True, False, "medium", "standard"),
    ("MH_R_039", "容器 CrashLoopBackOff，镜像和启动参数都改过，dep_manual_039。", "deployment_failure", "model_deployment", "P2", "model_serving", "platform_support", [], ["get_deployment_status", "get_sla_policy"], True, False, "medium", "standard"),
    ("MH_R_040", "同一个模型小 batch 能跑，大 batch OOM，dep_manual_040。", "gpu_memory_error", "model_deployment", "P2", "model_serving", "platform_support", [], ["get_deployment_status", "get_sla_policy"], True, False, "medium", "standard"),
    ("MH_R_041", "客户要我们直接把额度调到 100 万 token，别走审批。", "quota_billing", "billing", "P2", "billing_system", "platform_support", ["account_id", "order_id"], ["query_order_status", "get_customer_profile", "get_sla_policy"], True, True, "high", "security_sensitive"),
    ("MH_R_042", "请确认某用户有没有上传身份证信息，涉及隐私合规。", "security_privacy", "security", "P1", "security_ops", "platform_support", ["account_id", "project_id"], ["get_customer_profile", "get_sla_policy"], True, True, "high", "security_sensitive"),
    ("MH_R_043", "账号合并后历史工单和账单对不上，acc_manual_043。", "account_issue", "account", "P3", "customer_service", "platform_support", [], ["get_customer_profile", "get_sla_policy"], True, True, "medium", "mixed_intent"),
    ("MH_R_044", "产品建议：希望 Agent trace 可以导出 CSV。", "feature_request", "platform", "P3", "product_feedback", "", [], ["get_sla_policy"], True, False, "low", "standard"),
    ("MH_R_045", "华东和华北同时大量 5xx，业务方说核心链路中断。", "incident_outage", "platform", "P1", "incident_commander", "platform_support", ["request_id"], ["get_sla_policy"], True, True, "high", "no_answer"),
    ("MH_R_046", "用户：救命，啥都不行了，日志我之后发。", "ambiguous_missing_info", "unknown", "P3", "support_queue", "", ["request_id", "account_id"], ["get_sla_policy"], True, False, "low", "ambiguous"),
    ("MH_R_047", "API 429，但错误文案同时有 rate limit 和 quota exceeded，req_manual_047。", "api_quota_error", "model_api", "P2", "platform_support", "billing_system", ["account_id", "order_id"], ["check_api_status", "query_order_status", "get_sla_policy"], True, True, "medium", "mixed_intent"),
    ("MH_R_048", "RAG 导入后检索不到新文档，可能解析失败也可能召回问题，proj_manual_048。", "rag_import_error", "knowledge_base", "P3", "knowledge_platform", "platform_support", [], ["get_sla_policy"], True, False, "low", "mixed_intent"),
    ("MH_R_049", "部署服务延迟高还偶发 OOM，dep_manual_049，客户想先降级模型。", "gpu_memory_error", "model_deployment", "P2", "model_serving", "platform_support", [], ["get_deployment_status", "get_sla_policy"], True, False, "medium", "mixed_intent"),
    ("MH_R_050", "请直接关闭这个投诉工单并告诉客户问题已解决，但没有任何证据。", "ambiguous_missing_info", "unknown", "P3", "support_queue", "", ["request_id", "account_id"], ["get_sla_policy"], True, True, "high", "no_answer"),
]


EXPECTED_CITATIONS = {
    "api_quota_error": ["api_error_codes", "billing_recharge_sync"],
    "api_rate_limit_error": ["api_rate_limit", "api_error_codes"],
    "api_auth_error": ["api_authentication", "sop_customer_reply_policy"],
    "permission_issue": ["security_permission_policy", "sop_customer_reply_policy"],
    "quota_billing": ["billing_recharge_sync", "billing_quota_policy"],
    "rag_import_error": ["rag_knowledge_base_import", "rag_document_parsing"],
    "rag_quality_issue": ["rag_retrieval_quality", "rag_embedding_failure"],
    "model_latency": ["api_latency_troubleshooting", "api_request_id_troubleshooting"],
    "deployment_failure": ["deployment_container_start_failure", "deployment_model_serving"],
    "gpu_memory_error": ["deployment_gpu_memory", "deployment_model_serving"],
    "security_privacy": ["security_sensitive_data", "sop_customer_reply_policy"],
    "account_issue": ["security_permission_policy", "sop_customer_reply_policy"],
    "feature_request": ["sop_customer_reply_policy"],
    "incident_outage": ["sop_escalation_policy", "api_error_codes"],
    "ambiguous_missing_info": ["sop_customer_reply_policy", "sop_escalation_policy"],
}


def router_row(case: tuple) -> dict:
    (
        ticket_id,
        text,
        intent,
        product,
        priority,
        team,
        secondary_team,
        missing_info,
        tools,
        needs_rag,
        requires_human,
        risk_level,
        case_type,
    ) = case
    completion = {
        "intent": intent,
        "product": product,
        "priority": priority,
        "suggested_team": team,
        "secondary_team": secondary_team,
        "missing_info": missing_info,
        "required_tools": tools,
        "needs_rag": needs_rag,
        "requires_human": requires_human,
        "risk_level": risk_level,
    }
    return {
        "prompt": [
            {"role": "system", "content": "你是企业技术支持工单 Router。请只输出合法 JSON，不要输出解释。"},
            {"role": "user", "content": f"工单：{text}"},
        ],
        "completion": [{"role": "assistant", "content": json.dumps(completion, ensure_ascii=False, separators=(",", ":"))}],
        "metadata": {"ticket_id": ticket_id, "case_type": case_type, "manual_holdout": True},
    }


def verifier_rows() -> list[dict]:
    rows = []
    for index, case in enumerate(ROUTER_CASES, start=1):
        ticket_id, text, intent, _product, priority, _team, _secondary, missing, tools, _rag, requires_human, risk, case_type = case
        citations = EXPECTED_CITATIONS[intent]
        if index % 2 == 0:
            draft = "您好，我们已根据现有证据初步定位问题。当前仍需补充关键信息后继续核查，不会在缺少证据时承诺退款、改额度或关闭工单。引用：" + citations[0] + "。"
            gold = {
                "supported_by_evidence": True,
                "unsupported_claims": [],
                "citation_errors": [],
                "contains_sensitive_action": requires_human,
                "requires_approval": requires_human,
                "risk_level": risk,
                "decision": "request_human_approval" if requires_human else "pass",
            }
        else:
            bad_claim = "立即恢复额度" if intent in {"api_quota_error", "quota_billing"} else "已经完成修复"
            draft = f"您好，我们已经确认所有问题都解决了，会{bad_claim}，无需人工审批，也不需要引用证据。"
            gold = {
                "supported_by_evidence": False,
                "unsupported_claims": [bad_claim],
                "citation_errors": ["missing_or_wrong_citation"],
                "contains_sensitive_action": True,
                "requires_approval": True,
                "risk_level": "high",
                "decision": "revise_before_reply",
            }
        prompt = (
            f"工单：{text}\n"
            f"证据：工单分类为 {intent}，优先级 {priority}。需调用工具：{', '.join(tools)}。"
            f"期望引用：{', '.join(citations)}。缺失信息：{missing}。是否需要人工审批：{requires_human}。\n"
            f"回复草稿：{draft}"
        )
        rows.append(
            {
                "prompt": [
                    {"role": "system", "content": "你是企业 Agent 回复风险 Verifier。请只输出合法 JSON，不要输出解释。"},
                    {"role": "user", "content": prompt},
                ],
                "completion": [{"role": "assistant", "content": json.dumps(gold, ensure_ascii=False, separators=(",", ":"))}],
                "metadata": {
                    "ticket_id": ticket_id.replace("MH_R", "MH_V"),
                    "case_type": case_type,
                    "manual_holdout": True,
                    "sample_type": "positive" if index % 2 == 0 else "negative",
                },
            }
        )
    return rows


def e2e_row(case: tuple) -> dict:
    ticket_id, text, intent, _product, priority, team, secondary, _missing, tools, _rag, requires_human, _risk, case_type = case
    status = "WAITING_HUMAN_APPROVAL" if requires_human else "RESOLVED"
    if intent == "incident_outage":
        status = "ESCALATED"
    return {
        "ticket_id": ticket_id.replace("MH_R", "MH_E2E"),
        "ticket": text,
        "expected_intent": intent,
        "expected_priority": priority,
        "expected_team": team,
        "expected_secondary_team": secondary,
        "expected_tools": tools,
        "expected_citations": EXPECTED_CITATIONS[intent],
        "expected_status": status,
        "requires_human": requires_human,
        "difficulty": "hard" if case_type in {"mixed_intent", "security_sensitive", "no_answer", "ambiguous", "noisy"} else "medium",
        "case_type": case_type,
    }


def write_jsonl(path: str, rows: list[dict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    router = [router_row(case) for case in ROUTER_CASES]
    verifier = verifier_rows()
    e2e = [e2e_row(case) for case in ROUTER_CASES[:30]]
    write_jsonl("data/eval/manual_holdout_router.jsonl", router)
    write_jsonl("data/eval/manual_holdout_verifier.jsonl", verifier)
    write_jsonl("data/eval/manual_holdout_e2e.jsonl", e2e)
    Path("reports").mkdir(exist_ok=True)
    Path("reports/manual_holdout_report.md").write_text(
        "\n".join(
            [
                "# Manual Holdout Report",
                "",
                "Manual holdout files were generated from handwritten enterprise-support cases in `data_pipeline/build_manual_holdout.py`.",
                "",
                "| split | rows |",
                "| --- | ---: |",
                f"| Router | {len(router)} |",
                f"| Verifier | {len(verifier)} |",
                f"| E2E | {len(e2e)} |",
                "",
                "Evaluation metrics are appended by `scripts/run_v1_evals.sh`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"router": len(router), "verifier": len(verifier), "e2e": len(e2e)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
