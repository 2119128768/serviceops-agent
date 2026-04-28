from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.models import Base, ToolCall
from backend.database.seed import seed_database
from backend.tools import ToolRegistry


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


def test_tool_registry_logs_api_status_call():
    db = make_db()
    registry = ToolRegistry()
    result = registry.run(
        db, "ticket_2024_0331", "check_api_status", {"request_id": "req_20260427_001"}
    )
    assert result["found"] is True
    assert result["error_type"] == "quota_exceeded"
    assert db.query(ToolCall).count() == 1
