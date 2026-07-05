from __future__ import annotations

import json
from typing import Any

from core.database import Database
from services.reward_service import RewardService


class QuestService:
    def __init__(self, db: Database, game_data: Any | None = None) -> None:
        self.db = db
        self.game_data = game_data

    def quest_lookup(self) -> dict[str, dict[str, Any]]:
        quests = getattr(self.game_data, "quests", []) if self.game_data else []
        return {q["id"]: q for q in quests if "id" in q}

    def get_definition(self, quest_id: str) -> dict[str, Any] | None:
        return self.quest_lookup().get(quest_id)

    async def active_quests(self, discord_id: int):
        return await self.db.fetch(
            "SELECT quest_id, status, progress FROM player_quests WHERE discord_id=$1 AND status='active' ORDER BY created_at",
            discord_id,
        )

    async def completed_quests(self, discord_id: int):
        return await self.db.fetch(
            "SELECT quest_id, status, progress FROM player_quests WHERE discord_id=$1 AND status='completed' ORDER BY updated_at DESC",
            discord_id,
        )

    async def get_player_quest(self, discord_id: int, quest_id: str):
        return await self.db.fetchrow(
            "SELECT quest_id, status, progress FROM player_quests WHERE discord_id=$1 AND quest_id=$2",
            discord_id,
            quest_id,
        )

    async def start_quest(self, discord_id: int, quest_id: str) -> tuple[bool, str]:
        quest = self.get_definition(quest_id)
        if not quest:
            return False, "I couldn't find that quest."
        existing = await self.get_player_quest(discord_id, quest_id)
        if existing and existing["status"] == "active":
            return False, "That quest is already active."
        if existing and existing["status"] == "completed" and not quest.get("repeatable", False):
            return False, "You already completed that quest."
        await self.db.execute(
            """
            INSERT INTO player_quests(discord_id, quest_id, status, progress)
            VALUES($1, $2, 'active', '{}'::jsonb)
            ON CONFLICT(discord_id, quest_id)
            DO UPDATE SET status='active', progress='{}'::jsonb, updated_at=NOW()
            """,
            discord_id,
            quest_id,
        )
        return True, quest.get("start_dialogue", "Quest accepted.")

    async def abandon_quest(self, discord_id: int, quest_id: str) -> bool:
        result = await self.db.execute(
            "UPDATE player_quests SET status='abandoned', updated_at=NOW() WHERE discord_id=$1 AND quest_id=$2 AND status='active'",
            discord_id,
            quest_id,
        )
        return result.endswith("1")

    async def add_progress(self, discord_id: int, quest_id: str, key: str, amount: int = 1) -> None:
        row = await self.get_player_quest(discord_id, quest_id)
        if not row or row["status"] != "active":
            return
        progress = dict(row["progress"] or {})
        progress[key] = int(progress.get(key, 0)) + amount
        await self.db.execute(
            "UPDATE player_quests SET progress=$3::jsonb, updated_at=NOW() WHERE discord_id=$1 AND quest_id=$2",
            discord_id,
            quest_id,
            json.dumps(progress),
        )

    async def advance_kill(self, discord_id: int, enemy_id: str) -> None:
        rows = await self.active_quests(discord_id)
        for row in rows:
            quest = self.get_definition(row["quest_id"])
            if not quest:
                continue
            objective = quest.get("objective", {})
            if objective.get("type") != "kill":
                continue
            if objective.get("target") != enemy_id:
                continue
            progress = dict(row["progress"] or {})
            progress["kills"] = int(progress.get("kills", 0)) + 1
            await self.db.execute(
                "UPDATE player_quests SET progress=$3::jsonb, updated_at=NOW() WHERE discord_id=$1 AND quest_id=$2",
                discord_id,
                row["quest_id"],
                json.dumps(progress),
            )

    async def advance_boss_kill(self, discord_id: int, boss_id: str) -> None:
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
                json.dumps(progress),
            )

    def is_complete(self, quest: dict[str, Any], progress: dict[str, Any]) -> bool:
        objective = quest.get("objective", {})
        kind = objective.get("type")
        required = int(objective.get("amount", 1))
        if kind == "talk":
            return bool(progress.get("talked"))
        if kind == "explore":
            return bool(progress.get("explored"))
        if kind == "kill":
            return int(progress.get("kills", 0)) >= required
        if kind == "collect":
            return int(progress.get("collected", 0)) >= required
        return True

    async def turn_in(self, discord_id: int, quest_id: str) -> tuple[bool, str, dict[str, Any] | None]:
        row = await self.get_player_quest(discord_id, quest_id)
        if not row or row["status"] != "active":
            return False, "That quest is not active.", None
        quest = self.get_definition(quest_id)
        if not quest:
            return False, "Quest data is missing.", None
        progress = dict(row["progress"] or {})
        if not self.is_complete(quest, progress):
            return False, "You haven't completed the objective yet.", None
        rewards = quest.get("rewards", {})
        result = await RewardService(self.db, self.game_data).grant(discord_id, rewards)
        await self.db.execute(
            "UPDATE player_quests SET status='completed', updated_at=NOW() WHERE discord_id=$1 AND quest_id=$2",
            discord_id,
            quest_id,
        )
        return True, quest.get("complete_dialogue", "Quest complete."), result
