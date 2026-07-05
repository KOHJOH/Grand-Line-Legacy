from __future__ import annotations

from typing import Any

from core.database import Database
from services.inventory_service import InventoryService
from services.stat_service import StatService


class RewardService:
    def __init__(self, db: Database, game_data: Any) -> None:
        self.db = db
        self.game_data = game_data
        self.inventory = InventoryService(db)
        self.stats = StatService(db, game_data)

    async def grant(self, discord_id: int, rewards: dict[str, Any]) -> dict[str, Any]:
        xp = int(rewards.get("xp", 0))
        beli = int(rewards.get("beli", 0))
        items = rewards.get("items", {}) or {}
        level = None
        leveled = False
        if xp:
            level, leveled = await self.stats.grant_xp(discord_id, xp)
        if beli:
            await self.db.execute("UPDATE players SET beli=beli+$2, updated_at=NOW() WHERE discord_id=$1", discord_id, beli)
        for item_id, qty in items.items():
            await self.inventory.add_item(discord_id, item_id, int(qty))
        return {"xp": xp, "beli": beli, "items": items, "level": level, "leveled": leveled}
