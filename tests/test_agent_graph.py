from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.agents import ServiceOpsAgent
from backend.database.models import Base, Ticket, ToolCall
from backend.database.seed import seed_database
from backend.rag import HybridRetriever


def make_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed_database(session)
    return session


def test_agent_runs_quota_ticket_to_approval():
    db = make_db()
    ticket = Ticket(
        ticket_id="T_AGENT_001",
        subject="模型 API 返回 429，充值后仍无法调用",
        body="我们调用模型 API 时一直返回 429，控制台显示 quota exceeded。request_id: req_20260427_001",
        status="CREATED",
        missing_info=[],
        final_summary={},
    )
    db.add(ticket)
    db.commit()

    agent = ServiceOpsAgent(retriever=HybridRetriever("data/kb_docs"))
    result = agent.run(db, "T_AGENT_001")

    assert result["classification"]["intent"] == "api_quota_error"
    assert result["final_status"] == "WAITING_HUMAN_APPROVAL"
    assert result["approval"]["approval_id"].startswith("apr_")
    assert db.query(ToolCall).filter(ToolCall.ticket_id == "T_AGENT_001").count() >= 4
