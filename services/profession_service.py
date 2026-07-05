from __future__ import annotations

import random
from datetime import datetime, timezone

PROFESSIONS = {
    'fishing': {'label': 'Fishing', 'resource': 'fresh_fish', 'xp': (8, 16), 'beli': (20, 60)},
    'mining': {'label': 'Mining', 'resource': 'iron_ore', 'xp': (10, 18), 'beli': (25, 70)},
    'foraging': {'label': 'Foraging', 'resource': 'medicinal_herb', 'xp': (7, 14), 'beli': (15, 45)},
    'cooking': {'label': 'Cooking', 'resource': 'ration_pack', 'xp': (9, 17), 'beli': (20, 55)},
}

class ProfessionService:
    def __init__(self, db):
        self.db = db

    async def ensure(self, discord_id: int, profession: str):
        await self.db.execute(
            'INSERT INTO player_professions (discord_id, profession) VALUES ($1,$2) ON CONFLICT DO NOTHING',
            discord_id, profession,
        )
        return await self.db.fetchrow('SELECT * FROM player_professions WHERE discord_id=$1 AND profession=$2', discord_id, profession)

    async def gather(self, discord_id: int, profession: str):
        if profession not in PROFESSIONS:
            return None, 'Unknown profession. Try fishing, mining, foraging, or cooking.'
        player = await self.db.fetchrow('SELECT * FROM players WHERE discord_id=$1', discord_id)
        if not player:
            return None, 'Use /start first.'
        p = await self.ensure(discord_id, profession)
        meta = PROFESSIONS[profession]
        level = int(p['level'])
        xp_gain = random.randint(*meta['xp']) + level
        beli_gain = random.randint(*meta['beli']) + level * 5
        qty = random.randint(1, 2 + level // 5)
        await self.db.execute('UPDATE player_professions SET xp=xp+$1, total_actions=total_actions+1, last_action_at=NOW() WHERE discord_id=$2 AND profession=$3', xp_gain, discord_id, profession)
        await self.db.execute('UPDATE players SET beli=beli+$1, xp=xp+$2 WHERE discord_id=$3', beli_gain, max(1, xp_gain // 3), discord_id)
        await self.db.execute('INSERT INTO inventory_items (discord_id, item_id, quantity) VALUES ($1,$2,$3) ON CONFLICT (discord_id,item_id) DO UPDATE SET quantity=inventory_items.quantity+EXCLUDED.quantity', discord_id, meta['resource'], qty)
        await self.level_up(discord_id, profession)
        updated = await self.ensure(discord_id, profession)
        return {
            'profession': meta['label'], 'resource': meta['resource'], 'qty': qty,
            'xp': xp_gain, 'beli': beli_gain, 'level': updated['level'], 'total_xp': updated['xp']
        }, None

    async def level_up(self, discord_id: int, profession: str):
        p = await self.ensure(discord_id, profession)
        needed = int(p['level']) * 100
        if int(p['xp']) >= needed:
            await self.db.execute('UPDATE player_professions SET level=level+1, xp=xp-$1 WHERE discord_id=$2 AND profession=$3', needed, discord_id, profession)

    async def list_professions(self, discord_id: int):
        rows = []
        for prof in PROFESSIONS:
            rows.append(await self.ensure(discord_id, prof))
        return rows
