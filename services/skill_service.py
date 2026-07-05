from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SkillService:
    def __init__(self, db, data_path: str = 'data/skills/skills.json') -> None:
        self.db = db
        self.data_path = Path(data_path)
        self._skills: dict[str, dict[str, Any]] | None = None

    def skills(self) -> dict[str, dict[str, Any]]:
        if self._skills is None:
            payload = json.loads(self.data_path.read_text(encoding='utf-8')) if self.data_path.exists() else {'skills': []}
            self._skills = {s['id']: s for s in payload.get('skills', [])}
        return self._skills

    async def known(self, discord_id: int):
        rows = await self.db.fetch('SELECT skill_id, mastery, xp FROM player_skills WHERE discord_id=$1 ORDER BY skill_id', discord_id)
        return rows

    async def learn(self, discord_id: int, skill_id: str) -> tuple[bool, str]:
        skill = self.skills().get(skill_id)
        if not skill:
            return False, 'Unknown skill.'
        player = await self.db.fetchrow('SELECT level, beli FROM players WHERE discord_id=$1', discord_id)
        if not player:
            return False, 'Use `/start` first.'
        if int(player['level']) < int(skill.get('required_level', 1)):
            return False, f"You need level {skill.get('required_level')} to learn {skill['name']}."
        cost = int(skill.get('cost', 0))
        if int(player['beli']) < cost:
            return False, f"You need {cost:,} Beli to learn {skill['name']}."
        await self.db.execute('UPDATE players SET beli=beli-$2 WHERE discord_id=$1', discord_id, cost)
        await self.db.execute(
            '''INSERT INTO player_skills(discord_id, skill_id, mastery, xp) VALUES($1,$2,1,0)
               ON CONFLICT(discord_id, skill_id) DO UPDATE SET mastery=GREATEST(player_skills.mastery, 1), updated_at=NOW()''',
            discord_id, skill_id,
        )
        return True, f"Learned **{skill['name']}**."

    async def train(self, discord_id: int, skill_id: str) -> tuple[bool, str]:
        known = await self.db.fetchrow('SELECT mastery, xp FROM player_skills WHERE discord_id=$1 AND skill_id=$2', discord_id, skill_id)
        if not known:
            return False, 'Learn that skill first with `/learnskill`.'
        gained = 20
        xp = int(known['xp']) + gained
        mastery = int(known['mastery'])
        if xp >= mastery * 100:
            xp = 0
            mastery += 1
        await self.db.execute('UPDATE player_skills SET mastery=$3, xp=$4, updated_at=NOW() WHERE discord_id=$1 AND skill_id=$2', discord_id, skill_id, mastery, xp)
        return True, f"Trained skill. Mastery: **{mastery}**, XP: **{xp}/{mastery*100}**."
