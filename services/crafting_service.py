from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.database import Database
from services.inventory_ops import InventoryOps


class CraftingService:
    def __init__(self, db: Database, path: str = "data/crafting_recipes.json") -> None:
        self.db = db
        self.inv = InventoryOps(db)
        self.recipes = self._load(path)

    def _load(self, path: str) -> dict[str, dict[str, Any]]:
        p = Path(path)
        if not p.exists():
            return {}
        data = json.loads(p.read_text(encoding="utf-8"))
        return {r["id"]: r for r in data.get("recipes", [])}

    def all_recipes(self):
        return list(self.recipes.values())

    async def craft(self, discord_id: int, recipe_id: str) -> tuple[bool, str]:
        recipe = self.recipes.get(recipe_id)
        if not recipe:
            return False, "Unknown recipe."
        ingredients = recipe.get("ingredients", {})
        for item_id, qty in ingredients.items():
            if not await self.inv.has_item(discord_id, item_id, int(qty)):
                return False, f"Missing `{item_id}` x{qty}."
        for item_id, qty in ingredients.items():
            await self.inv.remove_item(discord_id, item_id, int(qty))
        result = recipe.get("result", {})
        await self.inv.add_item(discord_id, result.get("item_id", recipe_id), int(result.get("quantity", 1)))
        await self.db.execute(
            "INSERT INTO crafting_log(discord_id, recipe_id, result_item_id, quantity) VALUES($1,$2,$3,$4)",
            discord_id,
            recipe_id,
            result.get("item_id", recipe_id),
            int(result.get("quantity", 1)),
        )
        return True, f"Crafted **{recipe.get('name', recipe_id)}**."
