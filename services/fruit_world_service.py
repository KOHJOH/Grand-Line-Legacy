from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


class FruitWorldService:
    def __init__(self, db, data_path: str = 'data/fruits/fruit_world.json') -> None:
        self.db = db
        self.data_path = Path(data_path)
        self._fruits: dict[str, dict[str, Any]] | None = None

    def fruits(self) -> dict[str, dict[str, Any]]:
        if self._fruits is None:
            payload = json.loads(self.data_path.read_text(encoding='utf-8')) if self.data_path.exists() else {'fruits': []}
            self._fruits = {f['id']: f for f in payload.get('fruits', [])}
        return self._fruits

    async def spawn_random(self, island: str | None = None) -> tuple[bool, str]:
        fruits = list(self.fruits().values())
        if not fruits:
            return False, 'No fruit data loaded.'
        fruit = random.choice(fruits)
        island = island or random.choice(['Foosha Village','Shells Town','Orange Town','Syrup Village','Baratie','Arlong Park','Loguetown'])
        await self.db.execute(
            '''INSERT INTO fruit_spawns(fruit_id, fruit_name, island, rarity, expires_at)
               VALUES($1,$2,$3,$4,NOW() + INTERVAL '6 hours')''',
            fruit['id'], fruit['name'], island, fruit.get('rarity','Rare'),
        )
        return True, f"A **{fruit['name']}** has spawned somewhere on **{island}**."

    async def find(self, discord_id: int) -> tuple[bool, str]:
        player = await self.db.fetchrow('SELECT current_island FROM players WHERE discord_id=$1', discord_id)
        if not player:
            return False, 'Use `/start` first.'
        row = await self.db.fetchrow(
            '''SELECT * FROM fruit_spawns WHERE island=$1 AND claimed_by IS NULL AND expires_at > NOW()
               ORDER BY spawned_at ASC LIMIT 1''',
            player['current_island'],
        )
        if not row:
            return False, 'You searched the area but found no Devil Fruit.'
        await self.db.execute('UPDATE fruit_spawns SET claimed_by=$1, claimed_at=NOW() WHERE id=$2', discord_id, row['id'])
        await self.db.execute(
            '''INSERT INTO player_inventory(discord_id, item_id, quantity, metadata)
               VALUES($1,$2,1,$3::jsonb)
               ON CONFLICT(discord_id,item_id) DO UPDATE SET quantity=player_inventory.quantity+1''',
            discord_id, row['fruit_id'], json.dumps({'source':'fruit_spawn','fruit_name':row['fruit_name']}),
        )
        return True, f"You found **{row['fruit_name']}** and stored it in your inventory."

    async def active_spawns(self):
        return await self.db.fetch("SELECT fruit_name, island, rarity, expires_at FROM fruit_spawns WHERE claimed_by IS NULL AND expires_at > NOW() ORDER BY spawned_at DESC LIMIT 10")
