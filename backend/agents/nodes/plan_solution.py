from __future__ import annotations

from sqlalchemy.orm import Session

from backend.agents.state import AgentState
from backend.tracing.event_recorder import record_event


def plan_solution(db: Session, state: AgentState) -> AgentState:
    intent = state.router_output.get("intent")
    if intent == "api_quota_error":
        state.plan = _quota_plan(state)
    elif intent == "deployment_failure":
        state.plan = _deployment_plan(state)
    elif intent == "rag_retrieval_issue":
        state.plan = _rag_plan()
    else:
        state.plan = {
            "possible_causes": ["信息不足或问题类型未明确"],
            "steps": ["补充关键上下文", "检索相关 SOP", "必要时转人工支持队列"],
            "next_action": "request_more_info" if state.missing_info else "support_follow_up",
        }
    record_event(db, state.ticket_id, "solution_planned", state.plan)
    return state


def _quota_plan(state: AgentState) -> dict:
    api_status = _tool_result(state, "check_api_status")
    order_status = _tool_result(state, "query_order_status")
    causes = [
        "充值额度同步延迟或同步失败",
        "触发 QPS 限流但被误认为余额不足",
        "账号套餐绑定或额度策略不匹配",
        "请求落在异常服务节点或请求日志状态未刷新",
    ]
    steps = [
        "根据 request_id 查询 API 请求日志，区分 quota_exceeded 与 rate_limited。",
        "补齐 account_id 和 order_id 后查询订单支付状态与 quota_sync_status。",
        "如果订单已支付但 quota_sync_status 非 synced，升级计费系统组处理同步任务。",
        "如果是 QPS 限流，返回当前套餐限制、重试策略和升级建议。",
    ]
    if api_status.get("error_type") == "quota_exceeded" and order_status.get("quota_sync_status") == "failed":
        steps.insert(2, "当前 mock 数据显示订单已支付但额度同步失败，建议进入人工审批后升级计费系统组。")
    return {"possible_causes": causes, "steps": steps, "next_action": "human_approval"}


def _deployment_plan(state: AgentState) -> dict:
    deployment = _tool_result(state, "get_deployment_status")
    steps = [
        "读取部署状态与最新错误日志。",
        "核对模型大小、上下文长度、batch size、量化方式和 GPU 显存。",
        "优先建议降低 max_seq_length、启用量化或减小 batch size。",
        "如果调整后仍失败，升级模型服务组检查节点资源和镜像环境。",
    ]
    if "out of memory" in deployment.get("error_log", "").lower():
        steps.insert(2, "错误日志包含 OOM，优先检查 KV cache 与显存配置。")
    return {
        "possible_causes": ["GPU 显存不足", "上下文长度或批量配置过高", "模型服务配置不匹配"],
        "steps": steps,
        "next_action": "draft_reply",
    }


def _rag_plan() -> dict:
    return {
        "possible_causes": ["文档解析失败", "embedding 未刷新", "chunk 边界不合理", "metadata filter 过滤过严"],
        "steps": [
            "检查文档导入状态和 parser warning。",
            "比较 BM25、vector 和 hybrid 检索结果。",
            "确认新文档是否触发 embedding rebuild。",
            "检查 product、tenant、doc_type 等 metadata filter。",
        ],
        "next_action": "draft_reply",
    }


def _tool_result(state: AgentState, tool_name: str) -> dict:
    for item in state.tool_results:
        if item["tool_name"] == tool_name:
            return item["result"]
    return {}
