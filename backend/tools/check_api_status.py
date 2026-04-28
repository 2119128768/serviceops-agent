from __future__ import annotations

from sqlalchemy.orm import Session

from backend.database.models import APIRequest


def check_api_status(db: Session, request_id: str) -> dict:
    request = db.get(APIRequest, request_id)
    if not request:
        return {"found": False, "request_id": request_id}
    return {
        "found": True,
        "request_id": request.request_id,
        "account_id": request.account_id,
        "model_name": request.model_name,
        "status_code": request.status_code,
        "error_type": request.error_type,
        "latency_ms": request.latency_ms,
        "serving_region": request.serving_region,
        "created_at": request.created_at.isoformat(),
    }
