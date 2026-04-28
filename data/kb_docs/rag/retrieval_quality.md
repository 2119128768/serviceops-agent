# RAG Retrieval Quality Troubleshooting

当客户反馈“知识库导入后检索不到新文档”“新上传文档没有召回”“embedding 没更新”时，应按 RAG 检索质量问题处理。

Retrieval quality issues are usually caused by document parsing failures, stale embeddings, poor chunk boundaries, or missing metadata filters.

Recommended checks:

1. Confirm document import status.
2. Inspect chunk count and parser warnings.
3. Compare BM25, vector, and hybrid results.
4. Rebuild embeddings when source documents changed.
5. Use metadata filters for product, tenant, and document type when available.
