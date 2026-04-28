from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract a JSON object from model text without crashing on invalid output."""

    parsed = safe_json_loads(text)
    return parsed if isinstance(parsed, dict) else {}


def extract_first_json_object(text: str) -> str:
    """Return the first balanced JSON object candidate from arbitrary model text."""

    candidate = _strip_fences(text).strip()
    if candidate.startswith("{") and candidate.endswith("}"):
        return candidate

    start = candidate.find("{")
    if start == -1:
        return ""

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(candidate)):
        char = candidate[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return candidate[start : index + 1]
    return ""


def safe_json_loads(text: str) -> Any:
    """Parse JSON from raw JSON, fenced JSON, or leading/trailing model text."""

    candidate = _strip_fences(text).strip()
    snippets = [candidate]
    first = extract_first_json_object(candidate)
    if first and first not in snippets:
        snippets.append(first)

    for snippet in snippets:
        try:
            return json.loads(snippet)
        except (TypeError, json.JSONDecodeError):
            continue
    return {}


def normalize_list_fields(obj: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Ensure selected fields are lists so downstream scoring does not crash."""

    normalized = dict(obj)
    for field in fields:
        value = normalized.get(field)
        if value is None:
            normalized[field] = []
        elif isinstance(value, list):
            normalized[field] = value
        else:
            normalized[field] = [value]
    return normalized


def _strip_fences(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1)
    return text
