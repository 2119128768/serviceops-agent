from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from data_pipeline.common import read_jsonl


def build_report(rows: list[dict]) -> str:
    lines = ["# Dataset Stats", ""]
    lines.append(f"Total rows: {len(rows)}")
    lines.append("")
    _section(lines, "Intent Distribution", Counter(row["intent"] for row in rows))
    _section(lines, "Priority Distribution", Counter(row["priority"] for row in rows))
    _section(lines, "Difficulty Distribution", Counter(row["difficulty"] for row in rows))
    human_count = sum(1 for row in rows if row["requires_human"])
    lines.append("## Requires Human")
    lines.append("")
    lines.append(f"- count: {human_count}")
    lines.append(f"- ratio: {human_count / max(len(rows), 1):.4f}")
    lines.append("")
    tool_counts: Counter[str] = Counter()
    for row in rows:
        tool_counts.update(row["required_tools"])
    _section(lines, "Required Tools Distribution", tool_counts)
    return "\n".join(lines) + "\n"


def _section(lines: list[str], title: str, counter: Counter) -> None:
    lines.append(f"## {title}")
    lines.append("")
    lines.append("| item | count |")
    lines.append("| --- | ---: |")
    for item, count in sorted(counter.items(), key=lambda value: (-value[1], value[0])):
        lines.append(f"| {item} | {count} |")
    lines.append("")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/synthetic_tickets/ai_platform_tickets.jsonl")
    parser.add_argument("--output", default="reports/dataset_stats.md")
    args = parser.parse_args()

    rows = read_jsonl(args.input)
    report = build_report(rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
