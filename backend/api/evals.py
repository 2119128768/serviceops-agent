from __future__ import annotations

from fastapi import APIRouter

from backend.evals.metrics import exact_match, f1_for_list

router = APIRouter(prefix="/evals", tags=["evals"])


@router.get("/metric-spec")
def metric_spec():
    return {
        "router": [
            "json_valid_rate",
            "intent_accuracy",
            "priority_accuracy",
            "routing_accuracy",
            "missing_info_f1",
            "required_tools_accuracy",
            "requires_human_accuracy",
        ],
        "rag": ["top_k_hit_rate", "citation_accuracy", "context_recall"],
        "verifier": ["unsupported_claim_recall", "risk_detection_recall", "false_approval_rate"],
        "examples": {
            "exact_match": exact_match("P2", "P2"),
            "list_f1": f1_for_list(["account_id", "order_id"], ["account_id"]),
        },
    }
