from __future__ import annotations

import re

WORD_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    raw = [item.lower() for item in WORD_RE.findall(text)]
    tokens: list[str] = []
    chinese_buffer: list[str] = []
    for item in raw:
        if len(item) == 1 and "\u4e00" <= item <= "\u9fff":
            chinese_buffer.append(item)
            continue
        if chinese_buffer:
            tokens.extend(_flush_chinese(chinese_buffer))
            chinese_buffer = []
        tokens.append(item)
    if chinese_buffer:
        tokens.extend(_flush_chinese(chinese_buffer))
    return [token for token in tokens if token.strip()]


def _flush_chinese(chars: list[str]) -> list[str]:
    if len(chars) == 1:
        return chars
    return chars + ["".join(chars[i : i + 2]) for i in range(len(chars) - 1)]
