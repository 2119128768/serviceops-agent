from __future__ import annotations

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.tracing.event_recorder import record_event


def draft_reply(db: Session, state: AgentState) -> AgentState:
    citations = [
        f"{chunk['title']} ({chunk['doc_id']}#{chunk['chunk_id']})" for chunk in state.rag_chunks[:3]
    ]
    intent = state.router_output.get("intent", "general_support")

    if intent == "api_quota_error":
        state.draft_reply = _quota_reply(state, citations)
    elif intent == "deployment_failure":
        state.draft_reply = _deployment_reply(state, citations)
    elif intent == "rag_retrieval_issue":
        state.draft_reply = _rag_reply(state, citations)
    else:
        state.draft_reply = _generic_reply(state, citations)

    state.internal_note = _internal_note(state)
    record_event(
        db,
        state.ticket_id,
        "reply_drafted",
        {"draft_reply": state.draft_reply, "internal_note": state.internal_note, "citations": citations},
    )
    return state


def _quota_reply(state: AgentState, citations: list[str]) -> str:
    request_id = state.identifiers.get("request_id", "未提供")
    account_id = state.identifiers.get("account_id")
    missing = "、".join(state.missing_info) if state.missing_info else "无"
    order = _tool_result(state, "query_order_status")
    api = _tool_result(state, "check_api_status")

    known_lines = [
        f"我们已根据 request_id {request_id} 初步排查。",
        f"当前识别到的错误类型是 {api.get('error_type', '待确认')}。",
    ]
    if account_id:
        known_lines.append(f"请求关联账号为 {account_id}。")
    if order.get("found"):
        known_lines.append(
            f"最近订单状态为 {order.get('payment_status')}，额度同步状态为 {order.get('quota_sync_status')}。"
        )

    return (
        "您好，429 可能由额度不足、QPS 限流或额度同步延迟导致。"
        + "".join(known_lines)
        + f"目前仍需补充的信息：{missing}。"
        + "建议下一步核查订单支付状态、quota_sync_status 和账号套餐限制；"
        + "如果订单已支付但额度未同步，需要进入人工审批后升级计费系统组处理。"
        + _citation_text(citations)
    )


def _deployment_reply(state: AgentState, citations: list[str]) -> str:
    deployment = _tool_result(state, "get_deployment_status")
    return (
        "您好，我们已检查部署状态。"
        f"当前部署状态为 {deployment.get('status', '待确认')}，错误日志显示：{deployment.get('error_log', '暂无日志')}。"
        "建议先降低 max_seq_length 或 batch size，并确认是否启用量化；如果仍失败，升级模型服务组检查节点资源。"
        + _citation_text(citations)
    )


def _rag_reply(state: AgentState, citations: list[str]) -> str:
    return (
        "您好，知识库检索不到新文档通常与解析失败、embedding 未刷新、chunk 边界或 metadata filter 有关。"
        "建议先检查导入任务状态和 parser warning，再分别对比 BM25、向量和 hybrid 检索结果。"
        + _citation_text(citations)
    )


def _generic_reply(state: AgentState, citations: list[str]) -> str:
    return (
        "您好，我们已经收到问题并完成初步分类。请补充关键上下文后，我们会继续根据相关 SOP 和历史工单排查。"
        + _citation_text(citations)
    )


def _internal_note(state: AgentState) -> str:
    return (
        f"分类：{state.router_output.get('intent')}；优先级：{state.router_output.get('priority')}；"
        f"路由：{state.router_output.get('suggested_team')}；缺失信息：{state.missing_info}；"
        f"工具调用：{[item['tool_name'] for item in state.tool_results]}"
    )


def _citation_text(citations: list[str]) -> str:
    if not citations:
        return " 引用来源：暂无可靠引用，需要人工补充。"
    return " 引用来源：" + "；".join(citations) + "。"


def _tool_result(state: AgentState, tool_name: str) -> dict:
    for item in state.tool_results:
        if item["tool_name"] == tool_name:
            return item["result"]
    return {}
