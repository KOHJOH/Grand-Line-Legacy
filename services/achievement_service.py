from __future__ import annotations

import json
from pathlib import Path


class AchievementService:
    def __init__(self, db, data_path: str = 'data/achievements.json'):
        self.db = db
        self.achievements = json.loads(Path(data_path).read_text(encoding='utf-8')) if Path(data_path).exists() else []

    async def unlocked_ids(self, discord_id: int):
        rows = await self.db.fetch('SELECT achievement_id FROM player_achievements WHERE discord_id=$1', discord_id)
        return {r['achievement_id'] for r in rows}

    async def check(self, discord_id: int):
        player = await self.db.fetchrow('SELECT * FROM players WHERE discord_id=$1', discord_id)
        if not player:
            return []
        unlocked = await self.unlocked_ids(discord_id)
        new = []
        for ach in self.achievements:
            if ach['id'] in unlocked:
                continue
            stat = ach.get('stat')
            target = int(ach.get('target', 1))
            value = 0
            if stat == 'level':
                value = int(player['level'])
            elif stat == 'beli':
                value = int(player['beli'])
            elif stat == 'bounty':
                value = int(player.get('bounty', 0)) if hasattr(player, 'get') else int(player['bounty'] or 0)
            elif stat == 'crew':
                value = 1 if (player['crew'] and player['crew'] != 'None') else 0
            if value >= target:
                await self.db.execute('INSERT INTO player_achievements (discord_id, achievement_id) VALUES ($1,$2) ON CONFLICT DO NOTHING', discord_id, ach['id'])
                xp = int(ach.get('xp', 0)); beli = int(ach.get('beli', 0))
                if xp or beli:
                    await self.db.execute('UPDATE players SET xp=xp+$1, beli=beli+$2 WHERE discord_id=$3', xp, beli, discord_id)
                new.append(ach)
        return new

    async def list_for(self, discord_id: int):
        unlocked = await self.unlocked_ids(discord_id)
        return [(ach, ach['id'] in unlocked) for ach in self.achievements]
