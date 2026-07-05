from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from core.database import Database
from services.inventory_ops import InventoryOps


class FishingService:
    def __init__(self, db: Database, path: str = "data/fishing_tables.json") -> None:
        self.db = db
        self.inv = InventoryOps(db)
        self.tables = self._load(path)

    def _load(self, path: str) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {"default": [{"item_id": "small_fish", "name": "Small Fish", "weight": 100, "xp": 5}]}
        return json.loads(p.read_text(encoding="utf-8"))

    async def fish(self, discord_id: int, island: str) -> dict[str, Any]:
        pool = self.tables.get(island) or self.tables.get("default", [])
        catch = random.choices(pool, weights=[int(i.get("weight", 1)) for i in pool], k=1)[0]
        qty = random.randint(int(catch.get("min", 1)), int(catch.get("max", 1)))
        await self.inv.add_item(discord_id, catch["item_id"], qty)
        await self.db.execute(
            """
            INSERT INTO fishing_log(discord_id, island_id, item_id, quantity, xp_gained)
            VALUES($1,$2,$3,$4,$5)
            """,
            discord_id,
            island,
            catch["item_id"],
            qty,
            int(catch.get("xp", 5)),
        )
        await self.db.execute(
            """
            INSERT INTO professions(discord_id, profession, level, xp)
            VALUES($1,'fishing',1,$2)
            ON CONFLICT(discord_id, profession) DO UPDATE SET xp=professions.xp+EXCLUDED.xp, updated_at=NOW()
            """,
            discord_id,
            int(catch.get("xp", 5)),
        )
        return {"catch": catch, "quantity": qty}
