from __future__ import annotations

from core.database import Database

class QuestService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def active_quests(self, discord_id: int):
        return await self.db.fetch(
            "SELECT quest_id, status, progress FROM player_quests WHERE discord_id=$1 AND status='active'",
            discord_id,
        )

    async def start_quest(self, discord_id: int, quest_id: str):
        await self.db.execute(
            """
            INSERT INTO player_quests(discord_id, quest_id, status, progress)
            VALUES($1, $2, 'active', '{}'::jsonb)
            ON CONFLICT(discord_id, quest_id) DO NOTHING
            """,
            discord_id,
            quest_id,
        )


    async def advance_boss_kill(self, discord_id: int, boss_id: str) -> None:
        """Advance active quests whose progress JSON tracks boss kills.

        Static quest data can define boss objectives later, but this generic hook stores
        kills in each active quest's progress so turn-in logic can validate it.
        """
        rows = await self.active_quests(discord_id)
        for row in rows:
            progress = dict(row["progress"] or {})
            boss_kills = dict(progress.get("boss_kills", {}))
            boss_kills[boss_id] = int(boss_kills.get(boss_id, 0)) + 1
            progress["boss_kills"] = boss_kills
            await self.db.execute(
                "UPDATE player_quests SET progress=$3::jsonb, updated_at=NOW() WHERE discord_id=$1 AND quest_id=$2",
                discord_id,
                row["quest_id"],
                __import__("json").dumps(progress),
            )
