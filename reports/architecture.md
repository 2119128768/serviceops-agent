# ServiceOps Agent Architecture

## Goal

ServiceOps Agent handles enterprise AI platform support tickets through a traceable workflow:

1. Ticket intake
2. Router classification
3. Missing information detection
4. Enterprise knowledge retrieval
5. Historical ticket retrieval
6. Business tool calls
7. Solution planning
8. Customer reply drafting
9. Evidence and risk verification
10. Human approval
11. Knowledge update proposal

## Runtime Components

- `backend/main.py`: FastAPI application and router registration
- `backend/database/models.py`: SQLAlchemy models for tickets, trace events, tools, approvals, and mock business systems
- `backend/rag`: local hybrid retrieval implementation, replaceable with Qdrant/pgvector
- `backend/tools`: database-backed tool functions with persistent call logging
- `backend/agents`: stateful workflow nodes and graph orchestration
- `backend/evals`: Router, RAG, and end-to-end evaluation entrypoints
- `training/train_sft.py`: shared SFT/LoRA training script for Router and Verifier adapters
- `frontend/static`: local operator console

## Production Swap Points

- Replace `HashVectorRetriever` with real embeddings + Qdrant/pgvector.
- Replace `RouterModel` with Router LoRA served through vLLM.
- Replace `VerifierModel` with Verifier LoRA served through vLLM.
- Replace synchronous agent execution with Redis/Celery or LangGraph durable execution.
- Add authz before exposing account/order tools.

## Risk Controls

- Sensitive account, order, quota, refund, and official-reply actions require approval.
- Draft replies are checked for unsupported claims and weak citations.
- Tool calls persist arguments, results, success flag, and latency.
- Trace events persist every major state transition.
