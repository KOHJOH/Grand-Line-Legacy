from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.database import Database


@dataclass(slots=True)
class CalculatedStats:
    level: int
    hp: int
    max_hp: int
    stamina: int
    max_stamina: int
    attack: int
    defense: int
    speed: int
    crit_chance: float
    dodge_chance: float
    fruit_power: int
    haki_power: int
    bounty: int
    xp: int
    next_level_xp: int

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class StatService:
    def __init__(self, db: Database, game_data: Any) -> None:
        self.db = db
        self.game_data = game_data

    async def calculate(self, discord_id: int) -> CalculatedStats | None:
        player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return None

        level = int(player["level"])
        base_attack = 8 + level * 2
        base_defense = 5 + level
        base_speed = 5 + level // 2
        crit = 5.0
        dodge = 3.0

        equipment_bonus = await self._equipment_bonus(discord_id)
        haki_bonus = await self._haki_bonus(discord_id)
        fruit_bonus = await self._fruit_bonus(discord_id)

        attack = base_attack + equipment_bonus.get("attack", 0) + haki_bonus.get("attack", 0) + fruit_bonus.get("attack", 0)
        defense = base_defense + equipment_bonus.get("defense", 0) + haki_bonus.get("defense", 0)
        speed = base_speed + equipment_bonus.get("speed", 0) + haki_bonus.get("speed", 0)
        crit += equipment_bonus.get("crit", 0) + haki_bonus.get("crit", 0)
        dodge += equipment_bonus.get("dodge", 0) + haki_bonus.get("dodge", 0)

        return CalculatedStats(
            level=level,
            hp=int(player["hp"]),
            max_hp=int(player["max_hp"]),
            stamina=int(player["stamina"]),
            max_stamina=int(player["max_stamina"]),
            attack=max(1, attack),
            defense=max(0, defense),
            speed=max(1, speed),
            crit_chance=min(60.0, max(0.0, crit)),
            dodge_chance=min(45.0, max(0.0, dodge)),
            fruit_power=fruit_bonus.get("fruit_power", 0),
            haki_power=haki_bonus.get("haki_power", 0),
            bounty=int(player.get("bounty", 0)) if hasattr(player, "get") else int(player["bounty"]),
            xp=int(player["xp"]),
            next_level_xp=self.next_level_xp(level),
        )

    @staticmethod
    def next_level_xp(level: int) -> int:
        return 100 + (level - 1) * 75

    async def grant_xp(self, discord_id: int, amount: int) -> tuple[int, bool]:
        player = await self.db.fetchrow("SELECT level, xp FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return 0, False
        level = int(player["level"])
        xp = int(player["xp"]) + max(0, amount)
        leveled = False
        while xp >= self.next_level_xp(level):
            xp -= self.next_level_xp(level)
            level += 1
            leveled = True
        hp_gain = 10 if leveled else 0
        stamina_gain = 5 if leveled else 0
        await self.db.execute(
            """
            UPDATE players
            SET level=$2,
                xp=$3,
                max_hp=max_hp+$4,
                hp=LEAST(max_hp+$4, hp+$4),
                max_stamina=max_stamina+$5,
                stamina=LEAST(max_stamina+$5, stamina+$5),
                updated_at=NOW()
            WHERE discord_id=$1
            """,
            discord_id,
            level,
            xp,
            hp_gain,
            stamina_gain,
        )
        return level, leveled

    async def _equipment_bonus(self, discord_id: int) -> dict[str, int]:
        row = await self.db.fetchrow("SELECT * FROM player_equipment WHERE discord_id=$1", discord_id)
        if not row:
            return {}
        bonuses: dict[str, int] = {}
        item_ids = [row.get(k) if hasattr(row, "get") else row[k] for k in row.keys() if k.endswith("_item_id")]
        item_lookup = {item.get("id"): item for item in getattr(self.game_data, "items", [])}
        for item_id in item_ids:
            item = item_lookup.get(item_id)
            if not item:
                continue
            for stat, value in item.get("stats", {}).items():
                bonuses[stat] = bonuses.get(stat, 0) + int(value)
        return bonuses

    async def _haki_bonus(self, discord_id: int) -> dict[str, int]:
        row = await self.db.fetchrow("SELECT * FROM player_haki WHERE discord_id=$1", discord_id)
        if not row:
            return {}
        observation = int(row["observation_level"])
        armament = int(row["armament_level"])
        conqueror = int(row["conqueror_level"])
        return {
            "attack": armament // 5 + conqueror // 10,
            "defense": armament // 6,
            "speed": observation // 10,
            "crit": observation // 12,
            "dodge": observation // 10,
            "haki_power": observation + armament + conqueror,
        }

    async def _fruit_bonus(self, discord_id: int) -> dict[str, int]:
        row = await self.db.fetchrow("SELECT * FROM player_fruits WHERE discord_id=$1", discord_id)
        if not row:
            return {}
        mastery = int(row["mastery"])
        awakened = bool(row["awakened"])
        power = mastery + (50 if awakened else 0)
        return {"attack": mastery // 8 + (10 if awakened else 0), "fruit_power": power}
