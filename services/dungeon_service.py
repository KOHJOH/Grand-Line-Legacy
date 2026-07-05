from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from core.database import Database
from services.wallet_service import WalletService
from services.inventory_ops import InventoryOps


class DungeonService:
    def __init__(self, db: Database, path: str = "data/dungeons.json") -> None:
        self.db = db
        self.wallet = WalletService(db)
        self.inv = InventoryOps(db)
        self.dungeons = self._load(path)

    def _load(self, path: str) -> dict[str, dict[str, Any]]:
        p = Path(path)
        if not p.exists():
            return {}
        data = json.loads(p.read_text(encoding="utf-8"))
        return {d["id"]: d for d in data.get("dungeons", [])}

    def list_dungeons(self):
        return list(self.dungeons.values())

    async def enter(self, discord_id: int, dungeon_id: str) -> tuple[bool, str]:
        d = self.dungeons.get(dungeon_id)
        if not d:
            return False, "Unknown dungeon."
        player = await self.db.fetchrow("SELECT level, stamina FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return False, "Use `/start` first."
        if int(player["level"]) < int(d.get("level_required", 1)):
            return False, f"You need level {d.get('level_required', 1)}."
        if int(player["stamina"]) < int(d.get("stamina_cost", 20)):
            return False, "Not enough stamina. Use `/recover`."
        await self.db.execute("UPDATE players SET stamina=stamina-$2 WHERE discord_id=$1", discord_id, int(d.get("stamina_cost", 20)))
        await self.db.execute("UPDATE dungeon_runs SET status='abandoned' WHERE discord_id=$1 AND status='active'", discord_id)
        await self.db.execute(
            """
            INSERT INTO dungeon_runs(discord_id, dungeon_id, room, status, state)
            VALUES($1,$2,1,'active',$3::jsonb)
            """,
            discord_id,
            dungeon_id,
            json.dumps({"cleared": 0}),
        )
        return True, f"Entered **{d.get('name', dungeon_id)}**. Use `/dungeonaction` to progress."

    async def action(self, discord_id: int) -> tuple[bool, str]:
        run = await self.db.fetchrow("SELECT * FROM dungeon_runs WHERE discord_id=$1 AND status='active' ORDER BY started_at DESC LIMIT 1", discord_id)
        if not run:
            return False, "You are not inside a dungeon."
        d = self.dungeons.get(run["dungeon_id"], {})
        room = int(run["room"])
        total = int(d.get("rooms", 3))
        roll = random.randint(1, 100)
        if roll <= 65:
            xp = 20 + room * 10
            beli = 50 + room * 25
            await self.db.execute("UPDATE players SET xp=xp+$2, beli=beli+$3 WHERE discord_id=$1", discord_id, xp, beli)
            event = f"You cleared room {room}/{total}. +{xp} XP, +{beli:,} Beli."
        else:
            dmg = random.randint(8, 20)
            await self.db.execute("UPDATE players SET hp=GREATEST(1, hp-$2) WHERE discord_id=$1", discord_id, dmg)
            event = f"A trap hit you for {dmg} damage, but you pushed forward."
        if room >= total:
            reward = d.get("completion_reward", {})
            await self.wallet.add(discord_id, int(reward.get("beli", 250)), "dungeon_clear")
            if reward.get("item_id"):
                await self.inv.add_item(discord_id, reward["item_id"], int(reward.get("quantity", 1)))
            await self.db.execute("UPDATE dungeon_runs SET status='cleared', ended_at=NOW(), room=$2 WHERE id=$1", int(run["id"]), room)
            return True, event + f"\n🏆 Dungeon cleared! Bonus: {int(reward.get('beli',250)):,} Beli."
        await self.db.execute("UPDATE dungeon_runs SET room=room+1 WHERE id=$1", int(run["id"]))
        return True, event
