"""PostgreSQL repository using SQLAlchemy Core."""

from typing import Optional, Any
from sqlalchemy import text
from sqlalchemy.engine import Engine


class PostgresRepository:
    """Thin wrapper to keep SQL organized and parameterized."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def fetch_one(self, query: str, params: dict) -> Optional[dict]:
        """Execute a SELECT and return one row as dict."""
        stmt = text(query)
        with self.engine.connect() as conn:
            row = conn.execute(stmt, params).fetchone()
            return dict(row._mapping) if row else None

    def execute(self, query: str, params: dict) -> Any:
        """Execute a parameterized statement."""
        stmt = text(query)
        with self.engine.begin() as conn:
            return conn.execute(stmt, params)
