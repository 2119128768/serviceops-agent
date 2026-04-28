from __future__ import annotations

from sqlalchemy.orm import Session

from backend.database.models import Deployment


def get_deployment_status(db: Session, deployment_id: str) -> dict:
    deployment = db.get(Deployment, deployment_id)
    if not deployment:
        return {"found": False, "deployment_id": deployment_id}
    return {
        "found": True,
        "deployment_id": deployment.deployment_id,
        "account_id": deployment.account_id,
        "model_name": deployment.model_name,
        "status": deployment.status,
        "error_log": deployment.error_log,
        "gpu_memory": deployment.gpu_memory,
        "updated_at": deployment.updated_at.isoformat(),
    }
