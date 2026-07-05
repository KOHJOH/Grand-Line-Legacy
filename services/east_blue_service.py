from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class EastBlueService:
    def __init__(self, db, data_path: str = 'data/east_blue/islands.json') -> None:
        self.db = db
        self.data_path = Path(data_path)
        self._islands: dict[str, dict[str, Any]] | None = None

    def islands(self) -> dict[str, dict[str, Any]]:
        if self._islands is None:
            if not self.data_path.exists():
                self._islands = {}
            else:
                payload = json.loads(self.data_path.read_text(encoding='utf-8'))
                self._islands = {item['id']: item for item in payload.get('islands', [])}
        return self._islands

    def get(self, island_id: str) -> dict[str, Any] | None:
        key = island_id.lower().replace(' ', '_')
        return self.islands().get(key)

    def all_unlocked_for_level(self, level: int) -> list[dict[str, Any]]:
        return [island for island in self.islands().values() if int(island.get('required_level', 1)) <= level]

    async def get_player_location(self, discord_id: int) -> str:
        row = await self.db.fetchrow('SELECT current_island FROM players WHERE discord_id=$1', discord_id)
        return row['current_island'] if row and row['current_island'] else 'foosha_village'

    async def map_embed_rows(self, discord_id: int) -> tuple[list[dict[str, Any]], str, int]:
        player = await self.db.fetchrow('SELECT level, current_island FROM players WHERE discord_id=$1', discord_id)
        level = int(player['level']) if player else 1
        current = player['current_island'] if player else 'Foosha Village'
        return self.all_unlocked_for_level(level), current, level

    async def travel(self, discord_id: int, destination: str) -> tuple[bool, str]:
        island = self.get(destination)
        if not island:
            return False, 'That island is not in the East Blue map yet.'
        player = await self.db.fetchrow('SELECT level, current_island, beli FROM players WHERE discord_id=$1', discord_id)
        if not player:
            return False, 'Use `/start` first.'
        required = int(island.get('required_level', 1))
        if int(player['level']) < required:
            return False, f"You need level {required}+ to travel to {island['name']}."
        cost = int(island.get('travel_cost', 0))
        if int(player['beli']) < cost:
            return False, f"You need {cost:,} Beli for supplies to reach {island['name']}."
        await self.db.execute(
            'UPDATE players SET current_island=$2, beli=beli-$3, updated_at=NOW() WHERE discord_id=$1',
            discord_id, island['name'], cost,
        )
        await self.db.execute(
            '''INSERT INTO island_discoveries(discord_id, island_id, discovered_at)
               VALUES($1,$2,NOW()) ON CONFLICT(discord_id,island_id) DO NOTHING''',
            discord_id, island['id'],
        )
        return True, f"You sailed to **{island['name']}**. {island.get('arrival_text','')}"

    async def checkpoints(self, discord_id: int) -> list[str]:
        rows = await self.db.fetch('SELECT island_id FROM island_discoveries WHERE discord_id=$1 ORDER BY discovered_at', discord_id)
        return [r['island_id'] for r in rows]
