from __future__ import annotations

from core.database import Database


class InventoryOps:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def add_item(self, discord_id: int, item_id: str, quantity: int = 1) -> None:
        await self.db.execute(
            """
            INSERT INTO player_inventory(discord_id, item_id, quantity)
            VALUES($1,$2,$3)
            ON CONFLICT(discord_id, item_id) DO UPDATE SET quantity=player_inventory.quantity+EXCLUDED.quantity
            """,
            discord_id,
            item_id,
            max(1, int(quantity)),
        )

    async def remove_item(self, discord_id: int, item_id: str, quantity: int = 1) -> bool:
        quantity = max(1, int(quantity))
        row = await self.db.fetchrow(
            "SELECT quantity FROM player_inventory WHERE discord_id=$1 AND item_id=$2",
            discord_id,
            item_id,
        )
        if not row or int(row["quantity"]) < quantity:
            return False
        await self.db.execute(
            "UPDATE player_inventory SET quantity=quantity-$3 WHERE discord_id=$1 AND item_id=$2",
            discord_id,
            item_id,
            quantity,
        )
        await self.db.execute("DELETE FROM player_inventory WHERE discord_id=$1 AND quantity<=0", discord_id)
        return True

    async def has_item(self, discord_id: int, item_id: str, quantity: int = 1) -> bool:
        row = await self.db.fetchrow(
            "SELECT quantity FROM player_inventory WHERE discord_id=$1 AND item_id=$2",
            discord_id,
            item_id,
        )
        return bool(row and int(row["quantity"]) >= quantity)
