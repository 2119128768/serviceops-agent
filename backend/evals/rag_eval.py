from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from backend.evals.metrics import mean
from backend.rag.embeddings import make_embedding_backend
from backend.rag.reranker import make_reranker
from backend.rag import HybridRetriever


def evaluate(
    queries_path: str | Path,
    top_k: int = 5,
    embedding_backend: str = "hash",
    reranker_backend: str = "none",
    retrieval_mode: str = "hybrid",
    details_output: str | Path | None = None,
) -> dict:
    rows = _read_jsonl(queries_path)
    retriever = HybridRetriever(
        embedding_backend=make_embedding_backend(embedding_backend),
        reranker=make_reranker(reranker_backend),
        retrieval_mode=retrieval_mode,
    )
    hits: list[float] = []
    citation_hits: list[float] = []
    latencies: list[float] = []
    details = []
    for row in rows:
        started = time.perf_counter()
        results = retriever.search(row["query"], top_k=top_k)
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)
        returned = [item["doc_id"] for item in results]
        expected = row["expected_doc_ids"]
        hit = bool(set(expected) & set(returned))
        expected_citations = row.get("expected_citation_ids", expected)
        citation_hit = bool(set(expected_citations) & set(returned))
        hits.append(1.0 if hit else 0.0)
        citation_hits.append(1.0 if citation_hit else 0.0)
        details.append(
            {
                "query": row["query"],
                "expected": expected,
                "expected_citations": expected_citations,
                "returned": returned,
                "hit": hit,
                "citation_hit": citation_hit,
                "latency_ms": round(latency_ms, 3),
            }
        )
    result = {
        "rows": len(rows),
        "top_k": top_k,
        "retrieval_mode": retrieval_mode,
        "embedding_backend": embedding_backend,
        "reranker": reranker_backend,
        "top_k_hit_rate": round(mean(hits), 4),
        "citation_hit_rate": round(mean(citation_hits), 4),
        "avg_latency_ms": round(mean(latencies), 3),
        "details_output": str(details_output) if details_output else None,
    }
    if details_output:
        _write_jsonl(details_output, details)
    return result


def run_ablation(queries_path: str | Path, top_k: int = 5) -> list[dict]:
    configs = [
        ("BM25 only", "bm25", "hash", "none"),
        ("Hash-vector only", "vector", "hash", "none"),
        ("Real embedding only", "vector", "sentence_transformer", "none"),
        ("Hybrid", "hybrid", "hash", "none"),
        ("Hybrid + reranker", "hybrid", "hash", "cross_encoder"),
    ]
    results = []
    for name, mode, embedding, reranker in configs:
        try:
            result = evaluate(
                queries_path,
                top_k=top_k,
                embedding_backend=embedding,
                reranker_backend=reranker,
                retrieval_mode=mode,
            )
            result["name"] = name
        except RuntimeError as exc:
            result = {
                "name": name,
                "retrieval_mode": mode,
                "embedding_backend": embedding,
                "reranker": reranker,
                "error": str(exc),
            }
        results.append(result)
    _write_ablation_report(results)
    return results


def _read_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: str | Path, rows: list[dict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _write_ablation_report(results: list[dict]) -> None:
    lines = [
        "# RAG Ablation",
        "",
        "| variant | retrieval | embedding | reranker | top_k_hit_rate | citation_hit_rate | avg_latency_ms | status |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in results:
        status = "ok" if "error" not in row else row["error"].replace("|", "/")
        lines.append(
            "| {name} | {retrieval_mode} | {embedding_backend} | {reranker} | {top} | {citation} | {latency} | {status} |".format(
                name=row.get("name", ""),
                retrieval_mode=row.get("retrieval_mode", ""),
                embedding_backend=row.get("embedding_backend", ""),
                reranker=row.get("reranker", ""),
                top=row.get("top_k_hit_rate", "n/a"),
                citation=row.get("citation_hit_rate", "n/a"),
                latency=row.get("avg_latency_ms", "n/a"),
                status=status[:120],
            )
        )
    Path("reports").mkdir(exist_ok=True)
    Path("reports/rag_ablation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", default=None)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--embedding-backend", choices=["hash", "sentence_transformer"], default="hash")
    parser.add_argument("--reranker", choices=["none", "cross_encoder"], default="none")
    parser.add_argument("--retrieval-mode", choices=["bm25", "vector", "hybrid"], default="hybrid")
    parser.add_argument("--details-output", default="reports/rag_eval_details.jsonl")
    parser.add_argument("--output", default=None, help="Alias for --details-output.")
    parser.add_argument("--ablation", action="store_true")
    args = parser.parse_args()
    dataset = args.dataset or args.queries or "data/eval/rag_eval.jsonl"
    details_output = args.output or args.details_output
    if args.ablation:
        result = run_ablation(dataset, top_k=args.top_k)
    else:
        result = evaluate(
            dataset,
            top_k=args.top_k,
            embedding_backend=args.embedding_backend,
            reranker_backend=args.reranker,
            retrieval_mode=args.retrieval_mode,
            details_output=details_output,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
