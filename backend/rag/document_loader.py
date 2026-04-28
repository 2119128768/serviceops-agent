from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class DocumentChunk:
    doc_id: str
    chunk_id: str
    title: str
    content: str
    source_path: str
    metadata: dict = field(default_factory=dict)


def load_markdown_chunks(root: str | Path, max_chars: int = 1200, overlap: int = 120) -> list[DocumentChunk]:
    root_path = Path(root)
    chunks: list[DocumentChunk] = []
    for path in sorted(root_path.rglob("*.md")):
        relative = path.relative_to(root_path)
        doc_id = "_".join(relative.with_suffix("").parts)
        text = path.read_text(encoding="utf-8")
        sections = _split_sections(text)
        chunk_index = 0
        for title, content in sections:
            for piece in _chunk_text(content, max_chars=max_chars, overlap=overlap):
                if not piece.strip():
                    continue
                chunk_index += 1
                chunks.append(
                    DocumentChunk(
                        doc_id=doc_id,
                        chunk_id=f"{doc_id}_{chunk_index:03d}",
                        title=title or relative.stem.replace("_", " ").title(),
                        content=piece.strip(),
                        source_path=str(path),
                        metadata={
                            "category": relative.parts[0] if len(relative.parts) > 1 else "general",
                            "file_name": relative.name,
                        },
                    )
                )
    return chunks


def _split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append((current_title, current_lines))
                current_lines = []
            current_title = line.lstrip("#").strip()
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    if not sections:
        return [("", text)]
    return [(title, "\n".join(lines).strip()) for title, lines in sections]


def _chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        split_at = max(text.rfind("\n", start, end), text.rfind("。", start, end))
        if split_at <= start + max_chars // 2:
            split_at = end
        chunks.append(text[start:split_at].strip())
        if split_at >= len(text):
            break
        start = max(split_at - overlap, 0)
    return chunks
