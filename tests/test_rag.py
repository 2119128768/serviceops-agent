from backend.rag import HybridRetriever


def test_hybrid_retriever_finds_quota_docs():
    retriever = HybridRetriever("data/kb_docs")
    results = retriever.search("429 quota exceeded 充值后无法调用", top_k=5)
    doc_ids = {item["doc_id"] for item in results}
    assert "api_error_codes" in doc_ids
    assert "billing_recharge_sync" in doc_ids or "billing_quota_policy" in doc_ids
