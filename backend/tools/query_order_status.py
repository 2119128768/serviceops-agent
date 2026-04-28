from __future__ import annotations

from sqlalchemy.orm import Session

from backend.database.models import Order


def query_order_status(db: Session, order_id: str | None = None, account_id: str | None = None) -> dict:
    if order_id:
        order = db.get(Order, order_id)
    elif account_id:
        order = (
            db.query(Order)
            .filter(Order.account_id == account_id)
            .order_by(Order.created_at.desc())
            .first()
        )
    else:
        return {"found": False, "reason": "order_id_or_account_id_required"}

    if not order:
        return {"found": False, "order_id": order_id, "account_id": account_id}

    return {
        "found": True,
        "order_id": order.order_id,
        "account_id": order.account_id,
        "amount": order.amount,
        "payment_status": order.payment_status,
        "quota_sync_status": order.quota_sync_status,
        "created_at": order.created_at.isoformat(),
    }
