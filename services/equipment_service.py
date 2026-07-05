from __future__ import annotations

from core.database import Database

EQUIPMENT_COLUMNS = {
    "weapon": "weapon_item_id",
    "armor": "armor_item_id",
    "accessory1": "accessory_1_item_id",
    "accessory2": "accessory_2_item_id",
    "tool": "tool_item_id",
    "cosmetic": "cosmetic_item_id",
}


class EquipmentService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def ensure_row(self, discord_id: int) -> None:
        await self.db.execute(
            "INSERT INTO player_equipment(discord_id) VALUES($1) ON CONFLICT(discord_id) DO NOTHING",
            discord_id,
        )

    async def get_equipment(self, discord_id: int):
        await self.ensure_row(discord_id)
        return await self.db.fetchrow(
            """
            SELECT weapon_item_id, armor_item_id, accessory_1_item_id, accessory_2_item_id,
                   tool_item_id, cosmetic_item_id
            FROM player_equipment
            WHERE discord_id=$1
            """,
            discord_id,
        )

    async def equip(self, discord_id: int, item_id: str, slot_column: str) -> None:
        if slot_column not in {
            "weapon_item_id", "armor_item_id", "accessory_1_item_id", "accessory_2_item_id", "tool_item_id", "cosmetic_item_id"
        }:
            raise ValueError("Invalid equipment slot")
        await self.ensure_row(discord_id)
        await self.db.execute(
            f"UPDATE player_equipment SET {slot_column}=$2, updated_at=NOW() WHERE discord_id=$1",
            discord_id,
            item_id,
        )

    async def unequip(self, discord_id: int, slot_name: str) -> bool:
        slot_column = EQUIPMENT_COLUMNS.get(slot_name.lower())
        if not slot_column:
            return False
        await self.ensure_row(discord_id)
        await self.db.execute(
            f"UPDATE player_equipment SET {slot_column}=NULL, updated_at=NOW() WHERE discord_id=$1",
            discord_id,
        )
        return True

    async def total_stats(self, discord_id: int, item_lookup) -> dict[str, int]:
        equipment = await self.get_equipment(discord_id)
        totals: dict[str, int] = {}
        for item_id in equipment:
            if not item_id:
                continue
            item = item_lookup(item_id)
            if not item:
                continue
            for stat, value in item.get("stats", {}).items():
                totals[stat] = totals.get(stat, 0) + int(value)
        return totals
