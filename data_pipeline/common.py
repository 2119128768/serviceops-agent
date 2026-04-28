from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = ROOT / "data/taxonomy/ticket_taxonomy.yaml"

ID_PATTERNS = {
    "request_id": r"req_[0-9]{8}_[0-9]{4}",
    "account_id": r"acc_[0-9]{4}",
    "order_id": r"ord_[0-9]{8}_[0-9]{4}",
    "deployment_id": r"dep_[a-z0-9_]+",
    "project_id": r"proj_[0-9]{4}",
}


def load_taxonomy(path: str | Path = TAXONOMY_PATH) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    return [json.loads(line) for line in file_path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def has_identifier(text: str, field: str) -> bool:
    pattern = ID_PATTERNS.get(field)
    return bool(pattern and re.search(pattern, text))


def dynamic_missing_info(text: str, expected: list[str]) -> list[str]:
    return [field for field in expected if not has_identifier(text, field)]


def split_rows(
    rows: list[dict[str, Any]],
    train_size: int = 800,
    val_size: int = 100,
    test_size: int = 200,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    fixed_total = train_size + val_size + test_size
    if len(rows) == fixed_total:
        return rows[:train_size], rows[train_size : train_size + val_size], rows[
            train_size + val_size : train_size + val_size + test_size
        ]
    train_end = int(len(rows) * 0.8)
    val_end = train_end + int(len(rows) * 0.1)
    return rows[:train_end], rows[train_end:val_end], rows[val_end:]


def stable_shuffle(rows: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    return shuffled


def count_by(rows: list[dict[str, Any]], field: str) -> Counter:
    return Counter(row.get(field, "unknown") for row in rows)
