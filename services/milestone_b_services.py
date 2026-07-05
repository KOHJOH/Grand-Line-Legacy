from __future__ import annotations

from pathlib import Path
import json
from dataclasses import dataclass

from core.fruits.registry import FruitRegistry


@dataclass(slots=True)
class EnemyTemplate:
    id: str
    name: str
    level: int
    hp: int
    attack: int
    defense: int
    speed: int
    xp: int
    beli: int
    bounty: int = 0
    boss: bool = False
    rarity: str = "Common"


class EnemyFactory:
    def __init__(self, path: str = "data/milestone_b/enemies.json"):
        p = Path(path)
        self.data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def create(self, enemy_id: str) -> EnemyTemplate:
        if enemy_id not in self.data:
            enemy_id = "mountain_bandit"
        raw = self.data[enemy_id]
        return EnemyTemplate(id=enemy_id, **raw)


class BattleStore:
    def __init__(self) -> None:
        self.active = {}

    def set(self, player_id: int, battle) -> None:
        self.active[player_id] = battle

    def get(self, player_id: int):
        return self.active.get(player_id)

    def clear(self, player_id: int) -> None:
        self.active.pop(player_id, None)


class MilestoneBServices:
    def __init__(self, db):
        self.db = db
        self.fruits = FruitRegistry()
        self.fruits.load()
        self.enemies = EnemyFactory()
        self.battles = BattleStore()

    async def ensure_player(self, user) -> dict:
        await self.db.execute(
            """
            INSERT INTO players
            (discord_id, username, level, xp, hp, max_hp, stamina, max_stamina, attack, defense, speed, beli, bounty, island, title)
            VALUES($1,$2,1,0,100,100,100,100,10,10,10,0,0,'Foosha Village','Rookie')
            ON CONFLICT(discord_id) DO NOTHING
            """,
            user.id,
            user.name,
        )
        row = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", user.id)
        return dict(row)

    async def give_fruit(self, discord_id: int, fruit_id: str) -> bool:
        if not self.fruits.exists(fruit_id):
            return False
        await self.db.execute(
            """
            INSERT INTO player_fruit_storage(discord_id, fruit_id)
            VALUES($1,$2)
            ON CONFLICT DO NOTHING
            """,
            discord_id,
            fruit_id,
        )
        return True

    async def eat_fruit(self, discord_id: int, fruit_id: str) -> tuple[bool, str]:
        fruit = self.fruits.get(fruit_id)
        if not fruit:
            return False, "Unknown fruit."

        player = await self.db.fetchrow("SELECT fruit FROM players WHERE discord_id=$1", discord_id)
        if player and player["fruit"]:
            return False, "You already have a Devil Fruit."

        await self.db.execute(
            "UPDATE players SET fruit=$1, fruit_mastery=0 WHERE discord_id=$2",
            fruit_id,
            discord_id,
        )
        await self.db.execute(
            "DELETE FROM player_fruit_storage WHERE discord_id=$1 AND fruit_id=$2",
            discord_id,
            fruit_id,
        )
        return True, f"You ate **{fruit.name}**."
