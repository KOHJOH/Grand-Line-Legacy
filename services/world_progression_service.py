from __future__ import annotations

from core.database import Database


class WorldProgressionService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def unlock_island(self, discord_id: int, island_id: str, reason: str = "progression") -> None:
        await self.db.execute(
            """
            INSERT INTO island_unlocks(discord_id, island_id, reason)
            VALUES($1,$2,$3)
            ON CONFLICT(discord_id, island_id) DO UPDATE SET reason=EXCLUDED.reason, unlocked_at=NOW()
            """,
            discord_id,
            island_id,
            reason,
        )

    async def is_unlocked(self, discord_id: int, island_id: str) -> bool:
        row = await self.db.fetchrow(
            "SELECT 1 FROM island_unlocks WHERE discord_id=$1 AND island_id=$2",
            discord_id,
            island_id,
        )
        return row is not None

    async def unlocked_islands(self, discord_id: int):
        return await self.db.fetch(
            "SELECT island_id, reason, unlocked_at FROM island_unlocks WHERE discord_id=$1 ORDER BY unlocked_at",
            discord_id,
        )

    async def set_checkpoint(self, discord_id: int, island_id: str) -> None:
        await self.db.execute(
            """
            INSERT INTO player_checkpoints(discord_id, island_id)
            VALUES($1,$2)
            ON CONFLICT(discord_id) DO UPDATE SET island_id=EXCLUDED.island_id, updated_at=NOW()
            """,
            discord_id,
            island_id,
        )

    async def checkpoint(self, discord_id: int) -> str:
        row = await self.db.fetchrow("SELECT island_id FROM player_checkpoints WHERE discord_id=$1", discord_id)
        return row["island_id"] if row else "Foosha Village"
