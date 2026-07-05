from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.database import Database


class RaidService:
    def __init__(self, db: Database, path: str = "data/raids.json") -> None:
        self.db = db
        self.raids = self._load(path)

    def _load(self, path: str) -> dict[str, dict[str, Any]]:
        p = Path(path)
        if not p.exists():
            return {}
        data = json.loads(p.read_text(encoding="utf-8"))
        return {r["id"]: r for r in data.get("raids", [])}

    def list_raids(self):
        return list(self.raids.values())

    async def create_lobby(self, leader_id: int, raid_id: str) -> tuple[bool, str]:
        raid = self.raids.get(raid_id)
        if not raid:
            return False, "Unknown raid."
        player = await self.db.fetchrow("SELECT level FROM players WHERE discord_id=$1", leader_id)
        if not player:
            return False, "Use `/start` first."
        if int(player["level"]) < int(raid.get("level_required", 1)):
            return False, f"You need level {raid.get('level_required', 1)}."
        await self.db.execute("UPDATE raid_lobbies SET status='cancelled' WHERE leader_id=$1 AND status='forming'", leader_id)
        row = await self.db.fetchrow(
            """
            INSERT INTO raid_lobbies(leader_id, raid_id, party)
            VALUES($1,$2,$3::jsonb)
            RETURNING id
            """,
            leader_id,
            raid_id,
            json.dumps([leader_id]),
        )
        return True, f"Raid lobby **#{row['id']}** created for **{raid.get('name', raid_id)}**."

    async def join_lobby(self, discord_id: int, lobby_id: int) -> tuple[bool, str]:
        lobby = await self.db.fetchrow("SELECT * FROM raid_lobbies WHERE id=$1 AND status='forming'", lobby_id)
        if not lobby:
            return False, "Lobby not found."
        party = json.loads(lobby["party"] or "[]") if isinstance(lobby["party"], str) else list(lobby["party"])
        if discord_id in party:
            return False, "You are already in this lobby."
        raid = self.raids.get(lobby["raid_id"], {})
        if len(party) >= int(raid.get("max_players", 4)):
            return False, "That lobby is full."
        party.append(discord_id)
        await self.db.execute("UPDATE raid_lobbies SET party=$2::jsonb, updated_at=NOW() WHERE id=$1", lobby_id, json.dumps(party))
        return True, f"Joined raid lobby #{lobby_id}."

    async def active_lobbies(self):
        return await self.db.fetch("SELECT * FROM raid_lobbies WHERE status='forming' ORDER BY created_at DESC LIMIT 10")
