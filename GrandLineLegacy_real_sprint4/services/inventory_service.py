from __future__ import annotations

from core.database import Database


class InventoryService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def list_inventory(self, discord_id: int):
        return await self.db.fetch(
            """
            SELECT item_id, quantity, locked, durability, max_durability, metadata
            FROM player_inventory
            WHERE discord_id=$1
            ORDER BY item_id
            """,
            discord_id,
        )

    async def get_item(self, discord_id: int, item_id: str):
        return await self.db.fetchrow(
            """
            SELECT item_id, quantity, locked, durability, max_durability, metadata
            FROM player_inventory
            WHERE discord_id=$1 AND item_id=$2
            """,
            discord_id,
            item_id,
        )

    async def add_item(
        self,
        discord_id: int,
        item_id: str,
        quantity: int = 1,
        durability: int | None = None,
        max_durability: int | None = None,
    ) -> None:
        if quantity <= 0:
            return
        await self.db.execute(
            """
            INSERT INTO player_inventory(discord_id, item_id, quantity, durability, max_durability)
            VALUES($1, $2, $3, $4, $5)
            ON CONFLICT(discord_id, item_id)
            DO UPDATE SET quantity = player_inventory.quantity + EXCLUDED.quantity
            """,
            discord_id,
            item_id,
            quantity,
            durability,
            max_durability,
        )

    async def remove_item(self, discord_id: int, item_id: str, quantity: int = 1) -> bool:
        row = await self.get_item(discord_id, item_id)
        if not row or row["locked"] or row["quantity"] < quantity:
            return False
        new_quantity = row["quantity"] - quantity
        if new_quantity <= 0:
            await self.db.execute(
                "DELETE FROM player_inventory WHERE discord_id=$1 AND item_id=$2",
                discord_id,
                item_id,
            )
        else:
            await self.db.execute(
                "UPDATE player_inventory SET quantity=$3 WHERE discord_id=$1 AND item_id=$2",
                discord_id,
                item_id,
                new_quantity,
            )
        return True

    async def lock_item(self, discord_id: int, item_id: str, locked: bool) -> bool:
        result = await self.db.execute(
            "UPDATE player_inventory SET locked=$3 WHERE discord_id=$1 AND item_id=$2",
            discord_id,
            item_id,
            locked,
        )
        return result.endswith("1")

    async def use_consumable(self, discord_id: int, item_id: str, effects: dict[str, int]) -> tuple[bool, str]:
        removed = await self.remove_item(discord_id, item_id, 1)
        if not removed:
            return False, "You don't have that item, or it is locked."
        hp = int(effects.get("hp", 0))
        stamina = int(effects.get("stamina", 0))
        if hp or stamina:
            await self.db.execute(
                """
                UPDATE players
                SET hp = LEAST(max_hp, hp + $2),
                    stamina = LEAST(max_stamina, stamina + $3),
                    updated_at = NOW()
                WHERE discord_id=$1
                """,
                discord_id,
                hp,
                stamina,
            )
        parts = []
        if hp:
            parts.append(f"+{hp} HP")
        if stamina:
            parts.append(f"+{stamina} stamina")
        return True, ", ".join(parts) if parts else "Used."
