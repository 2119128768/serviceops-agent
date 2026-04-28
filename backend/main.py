from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api import approvals, evals, metrics, rag, tickets
from backend.database.seed import seed_database, should_auto_seed
from backend.database.session import SessionLocal, init_db

app = FastAPI(
    title="ServiceOps Agent",
    description="Enterprise ticket-processing Agent with RAG, tools, approval, and trace.",
    version="0.1.0",
)

app.include_router(tickets.router)
app.include_router(approvals.router)
app.include_router(rag.router)
app.include_router(metrics.router)
app.include_router(evals.router)

STATIC_DIR = Path("frontend/static")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()
    if should_auto_seed():
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()


@app.get("/")
def index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"service": "serviceops-agent", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
