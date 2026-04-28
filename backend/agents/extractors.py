from __future__ import annotations

import re


PATTERNS = {
    "request_id": r"req_[A-Za-z0-9_]+",
    "account_id": r"acc_[A-Za-z0-9_]+",
    "order_id": r"ord_[A-Za-z0-9_]+",
    "deployment_id": r"dep_[A-Za-z0-9_]+",
    "project_id": r"proj_[A-Za-z0-9_]+",
}


def extract_identifiers(text: str) -> dict[str, str]:
    identifiers: dict[str, str] = {}
    for name, pattern in PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            identifiers[name] = match.group(0)
    return identifiers
