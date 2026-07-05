from __future__ import annotations

class BountyService:
    def __init__(self, db):
        self.db = db

    async def profile(self, discord_id: int):
        return await self.db.fetchrow('SELECT username, level, bounty, faction, title, beli FROM players WHERE discord_id=$1', discord_id)

    async def add_bounty(self, discord_id: int, amount: int, reason: str):
        if amount <= 0:
            return 'Amount must be positive.'
        player = await self.profile(discord_id)
        if not player:
            return 'Use /start first.'
        await self.db.execute('UPDATE players SET bounty=COALESCE(bounty,0)+$1 WHERE discord_id=$2', amount, discord_id)
        await self.db.execute('INSERT INTO bounty_logs (discord_id, amount, reason) VALUES ($1,$2,$3)', discord_id, amount, reason[:120])
        return f'Bounty increased by {amount:,} for: {reason}'

    async def leaderboard(self):
        return await self.db.fetch('SELECT discord_id, username, level, bounty FROM players ORDER BY bounty DESC NULLS LAST, level DESC LIMIT 10')
