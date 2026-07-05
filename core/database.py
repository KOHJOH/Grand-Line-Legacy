from __future__ import annotations

from pathlib import Path

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

    async def initialize_schema(self, schema_path: str = "sql/schema.sql") -> None:
        """Run the base schema and every additive migration in sql/*.sql.

        This keeps Railway deploys simple: every startup safely creates or updates
        the database without deleting player data. SQL files must be idempotent
        using CREATE TABLE IF NOT EXISTS / ALTER TABLE ... ADD COLUMN IF NOT EXISTS.
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        base_path = Path(schema_path)
        if not base_path.exists():
            raise FileNotFoundError(f"Missing database schema file: {schema_path}")

        paths = [base_path]
        sql_dir = base_path.parent
        if sql_dir.exists():
            for path in sorted(sql_dir.glob("*.sql")):
                if path.resolve() != base_path.resolve():
                    paths.append(path)

        async with self.pool.acquire() as conn:
            for path in paths:
                sql = path.read_text(encoding="utf-8").strip()
                if sql:
                    await conn.execute(sql)

    async def fetchrow(self, query: str, *args):
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args):
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args):
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def execute_many(self, query: str, args_iterable):
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            return await conn.executemany(query, args_iterable)
