# RAG Ablation

本报告比较不同 RAG retrieval 方案在 hard RAG eval 上的表现。RAG 的目标不是让模型“记住企业知识”，而是为 Planner、Writer 和 Verifier 提供可追溯 evidence。

## 指标结果

| variant | retrieval | embedding | reranker | top_k_hit_rate | citation_hit_rate | avg_latency_ms | status |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| BM25 only | bm25 | hash | none | 0.5 | 0.5 | 0.053 | ok |
| Hash-vector only | vector | hash | none | 0.72 | 0.72 | 0.202 | ok |
| Real embedding only | vector | sentence_transformer | none | n/a | n/a | n/a | sentence-transformers is not installed. Install it with `pip install -e '.[rag]'` or set EMBEDDING_BACKEND=hash. |
| Hybrid | hybrid | hash | none | 0.72 | 0.72 | 0.255 | ok |
| Hybrid + reranker | hybrid | hash | cross_encoder | n/a | n/a | n/a | sentence-transformers is not installed. Install it with `pip install -e '.[rag]'` or set RERANKER_BACKEND=none. |

## 指标解释

top-k hit 表示期望 evidence 文档是否出现在前 k 个检索结果中。如果 top-k hit 不够高，Writer 和 Verifier 很可能拿不到正确上下文。

citation hit 表示期望引用是否被命中。它比“看起来相关”更接近企业 Agent 的要求，因为正式回复需要可追溯依据。

avg_latency_ms 表示检索耗时。本地 hash-vector 和 BM25 都很快，但真实 embedding 和 reranker 会增加延迟，需要在质量和成本之间取舍。

## 结果解读

BM25-only 的 top-k/citation hit 为 `0.50 / 0.50`，说明关键词检索能覆盖一部分错误码、术语和 ID 场景，但对口语化、混合意图和语义表达不足。

Hash-vector only 达到 `0.72 / 0.72`，说明即使没有真实 SentenceTransformer Embedding，语义式 fallback 也能改善召回。

Hybrid 当前同样为 `0.72 / 0.72`，没有超过 hash-vector only，说明还需要更强的 metadata filter、chunk title 设计、query rewrite 或 reranker 才能继续提升。

Real embedding 和 Hybrid + reranker 当前不可用，因为本地未安装 `sentence-transformers`。报告保留 n/a，不伪造实验结果。

## 为什么 RAG 仍是瓶颈

hard RAG eval citation hit 为 `0.72`，意味着仍有约 28% 样本没有命中期望引用。在 End-to-End Agent 中，只要证据没找对，后续 Writer 和 Verifier 都会受影响：

- Writer 可能只能给泛泛建议。
- Verifier 可能因为 evidence 不足而拦截。
- success rate 会被 citation miss 拉低。

## 改进方向

- 增加 chunk title 和 metadata，使 `api`、`billing`、`deployment`、`security` 等类别更容易被过滤。
- 引入真实 SentenceTransformer Embedding。
- 引入 CrossEncoder Reranker。
- 针对 `429`、`quota`、`rate limit`、`recharge sync` 等混淆场景做 query rewrite。
- 在 RAG eval 中增加更细的错误分类，例如 keyword miss、semantic miss、metadata miss 和 duplicate chunk。
