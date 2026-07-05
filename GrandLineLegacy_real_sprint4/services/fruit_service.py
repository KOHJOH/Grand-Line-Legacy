from __future__ import annotations

import random
from typing import Any

from core.database import Database
from services.inventory_service import InventoryService

RARITY_WEIGHTS = {
    "common": 52,
    "uncommon": 28,
    "rare": 13,
    "epic": 5,
    "legendary": 1.5,
    "mythic": 0.45,
    "divine": 0.05,
}

RARITY_EMOJI = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟠",
    "mythic": "🔴",
    "divine": "🌌",
}


class FruitService:
    def __init__(self, db: Database, game_data: Any) -> None:
        self.db = db
        self.game_data = game_data
        self.fruits: dict[str, dict[str, Any]] = {fruit["id"]: fruit for fruit in game_data.fruits}

    def get(self, fruit_id: str) -> dict[str, Any] | None:
        return self.fruits.get(fruit_id)

    def fruit_item_id(self, fruit_id: str) -> str:
        return f"fruit_{fruit_id}"

    def display(self, fruit_id: str) -> str:
        fruit = self.get(fruit_id)
        return fruit["name"] if fruit else fruit_id

    def rarity_emoji(self, rarity: str) -> str:
        return RARITY_EMOJI.get(rarity.lower(), "⚪")

    async def get_player_fruit(self, discord_id: int):
        return await self.db.fetchrow("SELECT * FROM player_fruits WHERE discord_id=$1", discord_id)

    async def list_fruitdex(self, discord_id: int, limit: int = 25):
        return await self.db.fetch(
            """
            SELECT fruit_id, seen, owned, mastered, awakened
            FROM fruitdex_entries
            WHERE discord_id=$1
            ORDER BY fruit_id
            LIMIT $2
            """,
            discord_id,
            limit,
        )

    async def mark_seen(self, discord_id: int, fruit_id: str, owned: bool = False) -> None:
        await self.db.execute(
            """
            INSERT INTO fruitdex_entries(discord_id, fruit_id, seen, owned)
            VALUES($1, $2, TRUE, $3)
            ON CONFLICT(discord_id, fruit_id)
            DO UPDATE SET seen=TRUE,
                          owned=fruitdex_entries.owned OR EXCLUDED.owned,
                          updated_at=NOW()
            """,
            discord_id,
            fruit_id,
            owned,
        )

    async def find_fruit(self, discord_id: int, island_id: str) -> tuple[bool, str, dict[str, Any] | None]:
        """Alpha exploration hook. This adds a fruit item to inventory.

        The real ocean/island engine will later determine spawn points. For now,
        the command uses rarity weights and records the discovery in FruitDex.
        """
        fruits = list(self.fruits.values())
        weights = [RARITY_WEIGHTS.get(f.get("rarity", "common"), 1) for f in fruits]
        fruit = random.choices(fruits, weights=weights, k=1)[0]
        await InventoryService(self.db).add_item(discord_id, self.fruit_item_id(fruit["id"]), 1)
        await self.mark_seen(discord_id, fruit["id"], owned=False)
        return True, f"You found a mysterious fruit: {fruit['name']}.", fruit

    async def eat_fruit(self, discord_id: int, fruit_id: str) -> tuple[bool, str]:
        fruit = self.get(fruit_id)
        if not fruit:
            return False, "That fruit does not exist."
        current = await self.get_player_fruit(discord_id)
        if current:
            return False, f"You already have {self.display(current['fruit_id'])}. Devil Fruits cannot be swapped in alpha."
        item_id = self.fruit_item_id(fruit_id)
        removed = await InventoryService(self.db).remove_item(discord_id, item_id, 1)
        if not removed:
            return False, f"You need the inventory item `{item_id}` before eating that fruit. Use `/fruitfind` in alpha testing."
        await self.db.execute(
            """
            INSERT INTO fruit_registry(fruit_id, owner_discord_id, status, obtained_at, updated_at)
            VALUES($1, $2, 'owned', NOW(), NOW())
            ON CONFLICT(fruit_id)
            DO UPDATE SET owner_discord_id=$2, status='owned', obtained_at=NOW(), updated_at=NOW()
            """,
            fruit_id,
            discord_id,
        )
        await self.db.execute(
            """
            INSERT INTO player_fruits(discord_id, fruit_id)
            VALUES($1, $2)
            """,
            discord_id,
            fruit_id,
        )
        await self.mark_seen(discord_id, fruit_id, owned=True)
        return True, f"You ate the {fruit['name']} and gained its power."

    async def train(self, discord_id: int) -> tuple[bool, str]:
        current = await self.get_player_fruit(discord_id)
        if not current:
            return False, "You do not have a Devil Fruit yet."
        gain = random.randint(8, 18)
        new_xp = int(current["mastery_xp"]) + gain
        new_mastery = min(100, int(current["mastery"]) + (new_xp // 100))
        new_xp = new_xp % 100 if new_mastery < 100 else 0
        await self.db.execute(
            """
            UPDATE player_fruits
            SET mastery=$2, mastery_xp=$3, last_trained_at=NOW(), updated_at=NOW()
            WHERE discord_id=$1
            """,
            discord_id,
            new_mastery,
            new_xp,
        )
        if new_mastery >= 100:
            await self.db.execute(
                """
                INSERT INTO fruitdex_entries(discord_id, fruit_id, seen, owned, mastered)
                VALUES($1, $2, TRUE, TRUE, TRUE)
                ON CONFLICT(discord_id, fruit_id)
                DO UPDATE SET mastered=TRUE, updated_at=NOW()
                """,
                discord_id,
                current["fruit_id"],
            )
        return True, f"Fruit training complete. +{gain} mastery XP. Mastery is now {new_mastery}/100."

    async def use_ability(self, discord_id: int, ability_id: str) -> tuple[bool, str, dict[str, Any] | None]:
        current = await self.get_player_fruit(discord_id)
        if not current:
            return False, "You do not have a Devil Fruit.", None
        fruit = self.get(current["fruit_id"])
        if not fruit:
            return False, "Your fruit data is missing.", None
        ability = next((a for a in fruit.get("abilities", []) if a["id"] == ability_id), None)
        if not ability:
            return False, "That ability is not part of your fruit.", None
        if int(current["mastery"]) < int(ability.get("mastery_required", 0)):
            return False, f"You need {ability['mastery_required']} mastery to use {ability['name']}.", None
        cooldown = await self.db.fetchrow(
            "SELECT ready_at FROM fruit_cooldowns WHERE discord_id=$1 AND ability_id=$2 AND ready_at > NOW()",
            discord_id,
            ability_id,
        )
        if cooldown:
            return False, f"That ability is still cooling down until {cooldown['ready_at']:%H:%M:%S UTC}.", None
        player = await self.db.fetchrow("SELECT stamina FROM players WHERE discord_id=$1", discord_id)
        cost = int(ability.get("stamina_cost", 0))
        if not player or int(player["stamina"]) < cost:
            return False, f"You need {cost} stamina.", None
        await self.db.execute("UPDATE players SET stamina=stamina-$2 WHERE discord_id=$1", discord_id, cost)
        await self.db.execute(
            """
            INSERT INTO fruit_cooldowns(discord_id, ability_id, ready_at)
            VALUES($1, $2, NOW() + ($3 || ' seconds')::interval)
            ON CONFLICT(discord_id, ability_id)
            DO UPDATE SET ready_at=EXCLUDED.ready_at
            """,
            discord_id,
            ability_id,
            int(ability.get("cooldown_seconds", 10)),
        )
        return True, f"Used {ability['name']} for {ability.get('power', 0)} power.", ability

    async def awaken(self, discord_id: int) -> tuple[bool, str]:
        current = await self.get_player_fruit(discord_id)
        if not current:
            return False, "You do not have a Devil Fruit."
        fruit = self.get(current["fruit_id"])
        if not fruit or not fruit.get("awakenable"):
            return False, "This fruit has no known awakening."
        if int(current["mastery"]) < 100:
            return False, "You need Mastery 100 before awakening."
        if current["awakened"]:
            return False, "Your fruit is already awakened."
        await self.db.execute(
            """
            UPDATE player_fruits SET awakened=TRUE, updated_at=NOW()
            WHERE discord_id=$1
            """,
            discord_id,
        )
        await self.db.execute(
            """
            INSERT INTO fruitdex_entries(discord_id, fruit_id, seen, owned, mastered, awakened)
            VALUES($1, $2, TRUE, TRUE, TRUE, TRUE)
            ON CONFLICT(discord_id, fruit_id)
            DO UPDATE SET awakened=TRUE, mastered=TRUE, updated_at=NOW()
            """,
            discord_id,
            current["fruit_id"],
        )
        return True, f"{fruit['name']} has awakened. Title unlocked: {fruit.get('awakening', {}).get('title', 'Awakened User')}."
