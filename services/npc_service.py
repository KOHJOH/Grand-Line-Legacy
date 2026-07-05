from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class NPCService:
    def __init__(self, db, data_path: str = 'data/east_blue/npcs.json') -> None:
        self.db = db
        self.data_path = Path(data_path)
        self._npcs: dict[str, dict[str, Any]] | None = None

    def npcs(self) -> dict[str, dict[str, Any]]:
        if self._npcs is None:
            payload = json.loads(self.data_path.read_text(encoding='utf-8')) if self.data_path.exists() else {'npcs': []}
            self._npcs = {npc['id']: npc for npc in payload.get('npcs', [])}
        return self._npcs

    def npc(self, npc_id: str) -> dict[str, Any] | None:
        key = npc_id.lower().replace(' ', '_')
        return self.npcs().get(key)

    def by_island(self, island_name: str) -> list[dict[str, Any]]:
        return [n for n in self.npcs().values() if n.get('island','').lower() == island_name.lower()]

    async def list_for_player(self, discord_id: int) -> tuple[str, list[dict[str, Any]]]:
        row = await self.db.fetchrow('SELECT current_island FROM players WHERE discord_id=$1', discord_id)
        island = row['current_island'] if row else 'Foosha Village'
        return island, self.by_island(island)

    async def talk(self, discord_id: int, npc_id: str) -> tuple[bool, str, dict[str, Any] | None]:
        npc = self.npc(npc_id)
        if not npc:
            return False, 'That NPC is not available.', None
        player = await self.db.fetchrow('SELECT current_island FROM players WHERE discord_id=$1', discord_id)
        if not player:
            return False, 'Use `/start` first.', npc
        if npc.get('island','').lower() != player['current_island'].lower():
            return False, f"{npc['name']} is at {npc['island']}, not your current island.", npc
        state = await self.db.fetchrow('SELECT friendship, talks FROM npc_relationships WHERE discord_id=$1 AND npc_id=$2', discord_id, npc['id'])
        if state:
            friendship = int(state['friendship']) + 1
            talks = int(state['talks']) + 1
            await self.db.execute('UPDATE npc_relationships SET friendship=$3, talks=$4, updated_at=NOW() WHERE discord_id=$1 AND npc_id=$2', discord_id, npc['id'], friendship, talks)
        else:
            friendship, talks = 1, 1
            await self.db.execute('INSERT INTO npc_relationships(discord_id,npc_id,friendship,talks) VALUES($1,$2,$3,$4)', discord_id, npc['id'], friendship, talks)
        lines = npc.get('dialogue', ['...'])
        line = lines[(talks - 1) % len(lines)]
        return True, line, npc
