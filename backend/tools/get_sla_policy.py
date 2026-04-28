from __future__ import annotations

from sqlalchemy.orm import Session

from backend.database.models import SLAPolicy


def get_sla_policy(db: Session, priority: str) -> dict:
    policy = db.get(SLAPolicy, priority)
    if not policy:
        return {"found": False, "priority": priority}
    return {
        "found": True,
        "priority": policy.priority,
        "response_minutes": policy.response_minutes,
        "resolution_minutes": policy.resolution_minutes,
        "escalation_team": policy.escalation_team,
        "description": policy.description,
    }
