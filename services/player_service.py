from __future__ import annotations

from core.database import Database

STARTER_ITEMS = {
    "bread": 5,
    "water": 3,
    "wooden_sword": 1,
    "starter_map": 1,
    "boat_voucher": 1,
}

class PlayerService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_player(self, discord_id: int):
        return await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)

    async def create_player(self, discord_id: int, username: str):
        existing = await self.get_player(discord_id)
        if existing:
            return existing, False
        await self.db.execute(
            """
            INSERT INTO players(discord_id, username)
            VALUES($1, $2)
            """,
            discord_id,
            username,
        )
        for item_id, qty in STARTER_ITEMS.items():
            await self.db.execute(
                """
                INSERT INTO player_inventory(discord_id, item_id, quantity)
                VALUES($1, $2, $3)
                ON CONFLICT(discord_id, item_id)
                DO UPDATE SET quantity = player_inventory.quantity + EXCLUDED.quantity
                """,
                discord_id,
                item_id,
                qty,
            )
        return await self.get_player(discord_id), True
