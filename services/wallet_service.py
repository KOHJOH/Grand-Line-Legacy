from __future__ import annotations

from core.database import Database


class WalletService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def balance(self, discord_id: int) -> int:
        row = await self.db.fetchrow("SELECT beli FROM players WHERE discord_id=$1", discord_id)
        return int(row["beli"]) if row else 0

    async def add(self, discord_id: int, amount: int, reason: str = "system") -> int:
        row = await self.db.fetchrow(
            "UPDATE players SET beli=beli+$2, updated_at=NOW() WHERE discord_id=$1 RETURNING beli",
            discord_id,
            int(amount),
        )
        await self.db.execute(
            "INSERT INTO currency_ledger(discord_id, amount, reason) VALUES($1,$2,$3)",
            discord_id,
            int(amount),
            reason,
        )
        return int(row["beli"]) if row else 0

    async def spend(self, discord_id: int, amount: int, reason: str = "purchase") -> tuple[bool, int]:
        amount = int(amount)
        row = await self.db.fetchrow("SELECT beli FROM players WHERE discord_id=$1", discord_id)
        if not row or int(row["beli"]) < amount:
            return False, int(row["beli"]) if row else 0
        new_balance = await self.add(discord_id, -amount, reason)
        return True, new_balance
