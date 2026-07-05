from __future__ import annotations

import random
from typing import Any

from core.database import Database
from services.inventory_service import InventoryService


class LootService:
    def __init__(self, db: Database, game_data: Any) -> None:
        self.db = db
        self.game_data = game_data
        self.inventory = InventoryService(db)
        self.boss_tables = game_data.loot_tables.get("bosses", {})
        self.chest_tables = game_data.loot_tables.get("chests", {})

    def _roll_table(self, table: dict[str, Any]) -> dict[str, Any]:
        beli_min, beli_max = table.get("beli", [0, 0])
        xp_min, xp_max = table.get("xp", [0, 0])
        rewards = {
            "beli": random.randint(beli_min, beli_max),
            "xp": random.randint(xp_min, xp_max),
            "items": [],
        }
        for drop in table.get("drops", []):
            if random.random() <= float(drop.get("chance", 0)):
                qmin, qmax = drop.get("qty", [1, 1])
                rewards["items"].append({"item_id": drop["item_id"], "quantity": random.randint(qmin, qmax)})
        return rewards

    async def grant_rewards(self, discord_id: int, rewards: dict[str, Any], source_type: str, source_id: str) -> None:
        beli = int(rewards.get("beli", 0))
        xp = int(rewards.get("xp", 0))
        if beli or xp:
            await self.db.execute(
                """
                UPDATE players
                SET beli = beli + $2,
                    xp = xp + $3,
                    updated_at = NOW()
                WHERE discord_id=$1
                """,
                discord_id,
                beli,
                xp,
            )
        for item in rewards.get("items", []):
            await self.inventory.add_item(discord_id, item["item_id"], int(item.get("quantity", 1)))
        await self.db.execute(
            "INSERT INTO loot_history(discord_id, source_type, source_id, rewards) VALUES($1,$2,$3,$4::jsonb)",
            discord_id,
            source_type,
            source_id,
            __import__("json").dumps(rewards),
        )

    async def roll_boss(self, discord_id: int, boss_id: str) -> dict[str, Any]:
        table = self.boss_tables.get(boss_id) or self.boss_tables.get("default", {})
        rewards = self._roll_table(table)
        await self.grant_rewards(discord_id, rewards, "boss", boss_id)
        return rewards

    async def roll_chest(self, discord_id: int, chest_id: str) -> dict[str, Any]:
        table = self.chest_tables.get(chest_id) or self.chest_tables.get("starter_chest", {})
        rewards = self._roll_table(table)
        await self.grant_rewards(discord_id, rewards, "chest", chest_id)
        return rewards
