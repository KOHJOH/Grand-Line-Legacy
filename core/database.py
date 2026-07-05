from __future__ import annotations

from pathlib import Path
from typing import Any

import asyncpg


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def fetchrow(self, query: str, *args: Any):
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args: Any):
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args: Any):
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def execute_script(self, script: str) -> None:
        """Run a multi-statement SQL script against the database."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            await conn.execute(script)

    async def run_schema_file(self, path: str = "sql/schema.sql") -> None:
        """Create/update all required tables on startup.

        This is intentionally idempotent because schema.sql uses CREATE TABLE IF NOT EXISTS
        and ALTER TABLE ... IF NOT EXISTS statements.
        """
        schema_path = Path(path)
        if not schema_path.exists():
            raise FileNotFoundError(f"Database schema file not found: {schema_path.resolve()}")
        await self.execute_script(schema_path.read_text(encoding="utf-8"))
