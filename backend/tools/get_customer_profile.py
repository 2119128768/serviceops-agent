from __future__ import annotations

from sqlalchemy.orm import Session

from backend.database.models import Account


def get_customer_profile(db: Session, account_id: str) -> dict:
    account = db.get(Account, account_id)
    if not account:
        return {"found": False, "account_id": account_id}
    return {
        "found": True,
        "account_id": account.account_id,
        "customer_name": account.customer_name,
        "plan_type": account.plan_type,
        "quota_remaining": account.quota_remaining,
        "qps_limit": account.qps_limit,
        "risk_level": account.risk_level,
        "status": account.status,
        "updated_at": account.updated_at.isoformat(),
    }
