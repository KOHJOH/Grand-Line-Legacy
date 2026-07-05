from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ItemDefinition:
    id: str
    name: str
    type: str
    rarity: str
    description: str
    stackable: bool = True
    stats: dict[str, int] | None = None
    effects: dict[str, int] | None = None
    durability: int | None = None
    sell_value: int = 0


class ItemService:
    def __init__(self, game_data: Any) -> None:
        self.game_data = game_data
        self.items: dict[str, dict[str, Any]] = {item["id"]: item for item in game_data.items}

    def get(self, item_id: str) -> dict[str, Any] | None:
        return self.items.get(item_id)

    def require(self, item_id: str) -> dict[str, Any]:
        item = self.get(item_id)
        if not item:
            raise ValueError(f"Unknown item_id: {item_id}")
        return item

    def display_name(self, item_id: str) -> str:
        item = self.get(item_id)
        return item.get("name", item_id) if item else item_id

    def rarity_emoji(self, rarity: str) -> str:
        return {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟠",
            "mythic": "🔴",
            "divine": "🌌",
        }.get(rarity.lower(), "⚪")

    def can_equip(self, item_id: str) -> bool:
        item = self.get(item_id)
        return bool(item and item.get("type") in {"weapon", "armor", "accessory", "tool", "cosmetic"})

    def equipment_slot_for(self, item_id: str, preferred: str | None = None) -> str | None:
        item = self.get(item_id)
        if not item:
            return None
        item_type = item.get("type")
        if item_type == "weapon":
            return "weapon_item_id"
        if item_type == "armor":
            return "armor_item_id"
        if item_type == "tool":
            return "tool_item_id"
        if item_type == "cosmetic":
            return "cosmetic_item_id"
        if item_type == "accessory":
            if preferred in {"accessory_1_item_id", "accessory_2_item_id"}:
                return preferred
            return "accessory_1_item_id"
        return None
