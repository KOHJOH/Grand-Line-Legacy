from __future__ import annotations

import json
import random
from typing import Any

from core.database import Database
from services.inventory_service import InventoryService


class IslandService:
    """World/island service for travel, NPCs, shops, treasure, and discovery.

    Static world content lives in JSON files. Persistent player-specific state lives in
    PostgreSQL so the same island can feel different for each player.
    """

    def __init__(self, db: Database, game_data: Any) -> None:
        self.db = db
        self.game_data = game_data

    def get_island(self, island_id: str) -> dict[str, Any] | None:
        return next((i for i in self.game_data.islands if i["id"] == island_id), None)

    def get_current_island(self, player: Any) -> dict[str, Any] | None:
        return self.get_island(player["current_island"])

    def available_destinations(self, current_island_id: str) -> list[dict[str, Any]]:
        current = self.get_island(current_island_id)
        if not current:
            return []
        ids = set(current.get("travel_connections", []))
        return [i for i in self.game_data.islands if i["id"] in ids]

    async def travel(self, discord_id: int, destination_id: str) -> tuple[bool, str]:
        player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return False, "Use `/start` first."
        destination = self.get_island(destination_id)
        if not destination:
            return False, "Unknown island id. Use `/travelmenu` to see where you can go."
        current = self.get_island(player["current_island"])
        if current and destination_id not in current.get("travel_connections", []):
            return False, f"You cannot sail directly to **{destination['name']}** from here yet."
        if int(player["level"]) < int(destination.get("min_level", 1)):
            return False, f"Recommended minimum level is {destination.get('min_level', 1)}. Train more before heading there."
        await self.db.execute(
            "UPDATE players SET current_island=$2, updated_at=NOW() WHERE discord_id=$1",
            discord_id,
            destination_id,
        )
        await self.mark_discovered(discord_id, destination_id)
        return True, f"⛵ You arrived at **{destination['name']}**."

    async def mark_discovered(self, discord_id: int, island_id: str) -> None:
        await self.db.execute(
            """
            INSERT INTO island_discoveries(discord_id, island_id, visits, first_visited_at, last_visited_at)
            VALUES($1, $2, 1, NOW(), NOW())
            ON CONFLICT(discord_id, island_id)
            DO UPDATE SET visits = island_discoveries.visits + 1, last_visited_at = NOW()
            """,
            discord_id,
            island_id,
        )

    def npcs_on_island(self, island_id: str) -> list[dict[str, Any]]:
        return [n for n in getattr(self.game_data, "npcs", []) if n.get("island_id") == island_id]

    def npc(self, npc_id: str) -> dict[str, Any] | None:
        return next((n for n in getattr(self.game_data, "npcs", []) if n["id"] == npc_id), None)

    async def talk_to_npc(self, discord_id: int, npc_id: str) -> tuple[bool, str, dict[str, Any] | None]:
        npc = self.npc(npc_id)
        if not npc:
            return False, "Unknown NPC.", None
        player = await self.db.fetchrow("SELECT current_island FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return False, "Use `/start` first.", None
        if npc.get("island_id") != player["current_island"]:
            return False, "That NPC is not on your current island.", None
        row = await self.db.fetchrow(
            "SELECT friendship, talks FROM npc_relationships WHERE discord_id=$1 AND npc_id=$2",
            discord_id,
            npc_id,
        )
        friendship = int(row["friendship"]) if row else 0
        talks = int(row["talks"]) if row else 0
        dialogue = npc.get("dialogue", {})
        line = dialogue.get("friend") if friendship >= 50 and dialogue.get("friend") else dialogue.get("default", "...")
        await self.db.execute(
            """
            INSERT INTO npc_relationships(discord_id, npc_id, friendship, talks, last_talked_at)
            VALUES($1, $2, $3, 1, NOW())
            ON CONFLICT(discord_id, npc_id)
            DO UPDATE SET friendship = LEAST(100, npc_relationships.friendship + $3), talks = npc_relationships.talks + 1, last_talked_at = NOW()
            """,
            discord_id,
            npc_id,
            2 if npc.get("friendship") else 0,
        )
        return True, line, {"friendship": min(100, friendship + (2 if npc.get("friendship") else 0)), "talks": talks + 1}

    def shops_on_island(self, island_id: str) -> list[dict[str, Any]]:
        return [s for s in getattr(self.game_data, "shops", []) if s.get("island_id") == island_id]

    def shop(self, shop_id: str) -> dict[str, Any] | None:
        return next((s for s in getattr(self.game_data, "shops", []) if s["id"] == shop_id), None)

    async def buy_item(self, discord_id: int, shop_id: str, item_id: str, quantity: int = 1) -> tuple[bool, str]:
        if quantity <= 0:
            return False, "Quantity must be positive."
        player = await self.db.fetchrow("SELECT beli, current_island FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return False, "Use `/start` first."
        shop = self.shop(shop_id)
        if not shop or shop.get("island_id") != player["current_island"]:
            return False, "That shop is not available here."
        listing = next((x for x in shop.get("inventory", []) if x["item_id"] == item_id), None)
        if not listing:
            return False, "That shop does not sell this item."
        price = int(listing["price"]) * quantity
        if int(player["beli"]) < price:
            return False, f"You need {price} Beli."
        await self.db.execute("UPDATE players SET beli=beli-$2, updated_at=NOW() WHERE discord_id=$1", discord_id, price)
        await InventoryService(self.db).add_item(discord_id, item_id, quantity)
        return True, f"Bought `{quantity}x {item_id}` for {price} Beli."

    def treasures_on_island(self, island_id: str) -> list[dict[str, Any]]:
        return [t for t in getattr(self.game_data, "treasures", []) if t.get("island_id") == island_id]

    async def search_treasure(self, discord_id: int) -> tuple[bool, str]:
        player = await self.db.fetchrow("SELECT current_island FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return False, "Use `/start` first."
        treasures = self.treasures_on_island(player["current_island"])
        if not treasures:
            return False, "You search carefully, but there are no registered treasures here yet."
        # Prefer not-yet-found treasure.
        found_rows = await self.db.fetch("SELECT treasure_id FROM player_treasures WHERE discord_id=$1", discord_id)
        found = {r["treasure_id"] for r in found_rows}
        candidates = [t for t in treasures if t["id"] not in found]
        if not candidates:
            return False, "You have already claimed the known treasures here."
        treasure = random.choice(candidates)
        await self.db.execute(
            "INSERT INTO player_treasures(discord_id, treasure_id, island_id, found_at) VALUES($1, $2, $3, NOW()) ON CONFLICT DO NOTHING",
            discord_id,
            treasure["id"],
            player["current_island"],
        )
        rewards = []
        inv = InventoryService(self.db)
        for reward in treasure.get("rewards", []):
            await inv.add_item(discord_id, reward["item_id"], int(reward.get("quantity", 1)))
            rewards.append(f"{reward.get('quantity', 1)}x {reward['item_id']}")
        beli = int(treasure.get("beli", 0))
        if beli:
            await self.db.execute("UPDATE players SET beli=beli+$2, updated_at=NOW() WHERE discord_id=$1", discord_id, beli)
            rewards.append(f"{beli} Beli")
        return True, f"🎁 Found **{treasure['name']}**! Rewards: " + ", ".join(rewards)

    async def gather_resource(self, discord_id: int, resource_id: str | None = None) -> tuple[bool, str]:
        player = await self.db.fetchrow("SELECT current_island FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return False, "Use `/start` first."
        details = next((d for d in getattr(self.game_data, "island_details", []) if d["island_id"] == player["current_island"]), None)
        resources = list((details or {}).get("resources", ["oak_wood", "iron_ore", "medicinal_herb"]))
        chosen = resource_id if resource_id in resources else random.choice(resources)
        qty = random.randint(1, 3)
        await InventoryService(self.db).add_item(discord_id, chosen, qty)
        return True, f"🌿 Gathered `{qty}x {chosen}`."
