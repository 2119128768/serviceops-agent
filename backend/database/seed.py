from __future__ import annotations

import os

from sqlalchemy.orm import Session

from backend.database.models import (
    APIRequest,
    Account,
    Deployment,
    Incident,
    Order,
    SLAPolicy,
    Ticket,
    TicketEvent,
)


def should_auto_seed() -> bool:
    return os.getenv("SERVICEOPS_AUTO_SEED", "true").lower() in {"1", "true", "yes"}


def seed_database(db: Session) -> None:
    if db.query(Account).first():
        return

    db.add_all(
        [
            Account(
                account_id="acc_001",
                customer_name="星河智能科技",
                plan_type="enterprise-pro",
                quota_remaining=0,
                qps_limit=20,
                risk_level="medium",
                status="active",
            ),
            Account(
                account_id="acc_002",
                customer_name="北辰制造",
                plan_type="standard",
                quota_remaining=120000,
                qps_limit=5,
                risk_level="low",
                status="active",
            ),
            Account(
                account_id="acc_003",
                customer_name="云帆数据",
                plan_type="trial",
                quota_remaining=3000,
                qps_limit=2,
                risk_level="low",
                status="suspended",
            ),
        ]
    )

    db.add_all(
        [
            Order(
                order_id="ord_20260426_001",
                account_id="acc_001",
                amount=50000,
                payment_status="paid",
                quota_sync_status="failed",
            ),
            Order(
                order_id="ord_20260425_009",
                account_id="acc_002",
                amount=12000,
                payment_status="paid",
                quota_sync_status="synced",
            ),
            Order(
                order_id="ord_20260427_003",
                account_id="acc_003",
                amount=5000,
                payment_status="unpaid",
                quota_sync_status="not_started",
            ),
        ]
    )

    db.add_all(
        [
            APIRequest(
                request_id="req_20260427_001",
                account_id="acc_001",
                model_name="qwen-plus",
                status_code=429,
                error_type="quota_exceeded",
                latency_ms=43,
            ),
            APIRequest(
                request_id="req_20260427_002",
                account_id="acc_002",
                model_name="embedding-v3",
                status_code=429,
                error_type="rate_limited",
                latency_ms=51,
            ),
            APIRequest(
                request_id="req_20260427_003",
                account_id="acc_002",
                model_name="qwen-plus",
                status_code=200,
                error_type=None,
                latency_ms=830,
            ),
        ]
    )

    db.add_all(
        [
            Deployment(
                deployment_id="dep_gpu_001",
                account_id="acc_002",
                model_name="Qwen2.5-7B-Instruct",
                status="failed",
                error_log="CUDA out of memory while allocating KV cache",
                gpu_memory="24GB",
            ),
            Deployment(
                deployment_id="dep_api_002",
                account_id="acc_001",
                model_name="Qwen2.5-3B-Instruct",
                status="running",
                error_log="",
                gpu_memory="16GB",
            ),
        ]
    )

    db.add_all(
        [
            Incident(
                incident_id="inc_20260427_api_001",
                severity="P2",
                title="部分账号 quota sync 延迟",
                status="mitigating",
                affected_product="billing",
            )
        ]
    )

    db.add_all(
        [
            SLAPolicy(
                priority="P0",
                response_minutes=10,
                resolution_minutes=120,
                escalation_team="incident_commander",
                description="全局不可用、重大安全事故或核心客户生产阻断。",
            ),
            SLAPolicy(
                priority="P1",
                response_minutes=30,
                resolution_minutes=360,
                escalation_team="senior_support",
                description="重要功能大面积异常或高价值客户严重受阻。",
            ),
            SLAPolicy(
                priority="P2",
                response_minutes=240,
                resolution_minutes=1440,
                escalation_team="platform_support_lead",
                description="单客户主要功能受影响，需要跨团队协作处理。",
            ),
            SLAPolicy(
                priority="P3",
                response_minutes=720,
                resolution_minutes=4320,
                escalation_team="support_queue",
                description="一般咨询、配置问题或非阻断缺陷。",
            ),
        ]
    )

    historical = [
        Ticket(
            ticket_id="ticket_2024_0331",
            subject="充值后 API 仍返回 429",
            body="客户充值后额度未恢复，request_id 显示 quota_exceeded，最终定位为 quota_sync_status failed。",
            customer_id="acc_001",
            status="RESOLVED",
            intent="api_quota_error",
            product="model_api",
            priority="P2",
            suggested_team="platform_support,billing_system",
            risk_level="medium",
            missing_info=[],
            final_summary={
                "resolution": "计费系统补偿同步任务后恢复额度。",
                "root_cause": "billing event queue delayed",
            },
        ),
        Ticket(
            ticket_id="ticket_2025_0818",
            subject="部署 7B 模型时 OOM",
            body="客户在 24GB GPU 上部署 7B 模型，长上下文导致 KV cache OOM。",
            customer_id="acc_002",
            status="RESOLVED",
            intent="deployment_failure",
            product="model_deployment",
            priority="P2",
            suggested_team="model_serving",
            risk_level="low",
            missing_info=[],
            final_summary={
                "resolution": "降低 max_seq_length 并启用 4-bit 量化。",
                "root_cause": "GPU memory insufficient",
            },
        ),
    ]
    db.add_all(historical)
    for item in historical:
        db.add(
            TicketEvent(
                ticket_id=item.ticket_id,
                event_type="seed_historical_ticket",
                payload={"status": item.status, "intent": item.intent},
            )
        )

    db.commit()
