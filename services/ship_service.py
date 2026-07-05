from __future__ import annotations

import json
import random
from typing import Any

from core.database import Database
from services.inventory_service import InventoryService


class ShipService:
    """Player ship, sailing, and ocean encounter service.

    Sprint 8 intentionally keeps naval gameplay playable and lightweight:
    players can buy ships, set an active ship, sail connected routes, roll
    voyage encounters, repair, and upgrade. Later sprints can layer crew roles,
    cannons, ship combat, and fleet warfare on top of these tables.
    """

    def __init__(self, db: Database, game_data: Any) -> None:
        self.db = db
        self.game_data = game_data
        self.ships: dict[str, dict[str, Any]] = {ship["id"]: ship for ship in getattr(game_data, "ships", [])}
        self.islands: dict[str, dict[str, Any]] = {island["id"]: island for island in game_data.islands}
        self.encounters: list[dict[str, Any]] = list(getattr(game_data, "ocean_encounters", []))

    def ship_definition(self, ship_type: str) -> dict[str, Any] | None:
        return self.ships.get(ship_type)

    def shipyard_inventory(self) -> list[dict[str, Any]]:
        return sorted(self.ships.values(), key=lambda s: int(s.get("price", 0)))

    async def owned_ships(self, discord_id: int):
        return await self.db.fetch(
            """
            SELECT * FROM player_ships
            WHERE discord_id=$1
            ORDER BY active DESC, purchased_at ASC
            """,
            discord_id,
        )

    async def active_ship(self, discord_id: int):
        return await self.db.fetchrow(
            """
            SELECT * FROM player_ships
            WHERE discord_id=$1 AND active=TRUE
            LIMIT 1
            """,
            discord_id,
        )

    async def buy_ship(self, discord_id: int, ship_type: str, nickname: str | None = None) -> tuple[bool, str]:
        ship = self.ship_definition(ship_type)
        if not ship:
            return False, "Unknown ship type. Use `/shipyard` to see available ships."

        player = await self.db.fetchrow("SELECT beli FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return False, "Use `/start` first."

        price = int(ship.get("price", 0))
        if ship_type == "raft":
            existing_raft = await self.db.fetchrow(
                "SELECT id FROM player_ships WHERE discord_id=$1 AND ship_type='raft' LIMIT 1",
                discord_id,
            )
            if existing_raft:
                return False, "You already own a Starter Raft."
            # A starter raft may be claimed for free. If they still have a boat voucher, consume one.
            await InventoryService(self.db).remove_item(discord_id, "boat_voucher", 1)
        elif int(player["beli"]) < price:
            return False, f"You need {price:,} Beli to buy a {ship['name']}."
        else:
            await self.db.execute(
                "UPDATE players SET beli=beli-$2, updated_at=NOW() WHERE discord_id=$1",
                discord_id,
                price,
            )

        active_exists = await self.active_ship(discord_id)
        await self.db.execute(
            """
            INSERT INTO player_ships(
                discord_id, ship_type, nickname, hull_hp, max_hull_hp, speed,
                cargo_capacity, crew_capacity, cannon_slots, active
            )
            VALUES($1,$2,$3,$4,$4,$5,$6,$7,$8,$9)
            """,
            discord_id,
            ship_type,
            nickname or ship["name"],
            int(ship.get("hull_hp", 100)),
            int(ship.get("speed", 5)),
            int(ship.get("cargo_capacity", 10)),
            int(ship.get("crew_capacity", 1)),
            int(ship.get("cannon_slots", 0)),
            active_exists is None,
        )
        return True, f"Purchased **{nickname or ship['name']}**."

    async def set_active_ship(self, discord_id: int, ship_id: int) -> tuple[bool, str]:
        owned = await self.db.fetchrow(
            "SELECT * FROM player_ships WHERE id=$1 AND discord_id=$2",
            ship_id,
            discord_id,
        )
        if not owned:
            return False, "You do not own that ship."
        await self.db.execute("UPDATE player_ships SET active=FALSE WHERE discord_id=$1", discord_id)
        await self.db.execute("UPDATE player_ships SET active=TRUE WHERE id=$1", ship_id)
        return True, f"**{owned['nickname']}** is now your active ship."

    async def repair_active_ship(self, discord_id: int) -> tuple[bool, str]:
        ship = await self.active_ship(discord_id)
        if not ship:
            return False, "You need a ship first. Use `/shipyard` and `/buyship`."
        missing = int(ship["max_hull_hp"]) - int(ship["hull_hp"])
        if missing <= 0:
            return False, "Your active ship is already fully repaired."
        cost = max(50, missing * 3)
        player = await self.db.fetchrow("SELECT beli FROM players WHERE discord_id=$1", discord_id)
        if int(player["beli"]) < cost:
            return False, f"Repairs cost {cost:,} Beli."
        await self.db.execute(
            "UPDATE players SET beli=beli-$2, updated_at=NOW() WHERE discord_id=$1",
            discord_id,
            cost,
        )
        await self.db.execute(
            "UPDATE player_ships SET hull_hp=max_hull_hp, updated_at=NOW() WHERE id=$1",
            int(ship["id"]),
        )
        return True, f"Repaired **{ship['nickname']}** for {cost:,} Beli."

    async def upgrade_active_ship(self, discord_id: int, stat: str) -> tuple[bool, str]:
        allowed = {"speed", "hull", "cargo"}
        stat = stat.lower()
        if stat not in allowed:
            return False, "Upgrade must be one of: `speed`, `hull`, `cargo`."
        ship = await self.active_ship(discord_id)
        if not ship:
            return False, "You need a ship first."
        current_level = int(ship["upgrade_level"])
        if current_level >= 20:
            return False, "This ship has reached the current alpha upgrade cap."
        cost = 1000 + (current_level * 750)
        player = await self.db.fetchrow("SELECT beli FROM players WHERE discord_id=$1", discord_id)
        if int(player["beli"]) < cost:
            return False, f"Upgrade costs {cost:,} Beli."
        if stat == "speed":
            update = "speed=speed+1"
            desc = "+1 speed"
        elif stat == "hull":
            update = "max_hull_hp=max_hull_hp+75, hull_hp=hull_hp+75"
            desc = "+75 hull HP"
        else:
            update = "cargo_capacity=cargo_capacity+15"
            desc = "+15 cargo"
        await self.db.execute("UPDATE players SET beli=beli-$2, updated_at=NOW() WHERE discord_id=$1", discord_id, cost)
        await self.db.execute(
            f"UPDATE player_ships SET {update}, upgrade_level=upgrade_level+1, updated_at=NOW() WHERE id=$1",
            int(ship["id"]),
        )
        return True, f"Upgraded **{ship['nickname']}**: {desc}."

    async def sail(self, discord_id: int, destination_id: str) -> tuple[bool, str]:
        active_session = await self.active_travel_session(discord_id)
        if active_session:
            return False, "You are already sailing. Use `/voyage` to check progress."
        player = await self.db.fetchrow("SELECT current_island, level FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return False, "Use `/start` first."
        current_id = player["current_island"]
        current = self.islands.get(current_id)
        destination = self.islands.get(destination_id)
        if not destination:
            return False, "Unknown destination. Use `/travelmenu` or `/oceanmap`."
        if not current or destination_id not in current.get("travel_connections", []):
            return False, f"No known sea route from `{current_id}` to `{destination_id}`."
        if int(player["level"]) < int(destination.get("min_level", 1)):
            return False, f"Recommended minimum level for {destination['name']} is {destination.get('min_level', 1)}."
        ship = await self.active_ship(discord_id)
        if not ship:
            return False, "You need a ship before sailing. Claim a Starter Raft with `/buyship raft`."
        if int(ship["hull_hp"]) <= 0:
            return False, "Your active ship is wrecked. Repair it before sailing."
        speed = max(1, int(ship["speed"]))
        # Fast enough for Discord alpha testing, still clearly a voyage instead of teleport.
        duration_seconds = max(45, 240 - (speed * 12))
        await self.db.execute(
            """
            INSERT INTO travel_sessions(discord_id, origin_island, destination_island, ship_id, duration_seconds, ends_at)
            VALUES($1,$2,$3,$4,$5,NOW()+($5::int * INTERVAL '1 second'))
            """,
            discord_id,
            current_id,
            destination_id,
            int(ship["id"]),
            int(duration_seconds),
        )
        return True, f"Set sail from **{current['name']}** to **{destination['name']}**. Use `/voyage` during the trip. ETA: ~{duration_seconds}s."

    async def active_travel_session(self, discord_id: int):
        return await self.db.fetchrow(
            """
            SELECT * FROM travel_sessions
            WHERE discord_id=$1 AND status='sailing'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            discord_id,
        )

    async def voyage_status(self, discord_id: int) -> tuple[bool, str]:
        session = await self.active_travel_session(discord_id)
        if not session:
            return False, "You are not currently sailing. Use `/sail` to start a voyage."

        # Complete voyage if ETA has passed.
        remaining = await self.db.fetchrow(
            "SELECT EXTRACT(EPOCH FROM (ends_at - NOW()))::int AS seconds_left FROM travel_sessions WHERE id=$1",
            int(session["id"]),
        )
        seconds_left = int(remaining["seconds_left"] or 0)
        if seconds_left <= 0:
            await self.db.execute(
                "UPDATE travel_sessions SET status='arrived', updated_at=NOW() WHERE id=$1",
                int(session["id"]),
            )
            await self.db.execute(
                "UPDATE players SET current_island=$2, updated_at=NOW() WHERE discord_id=$1",
                discord_id,
                session["destination_island"],
            )
            await self.db.execute(
                """
                INSERT INTO island_discoveries(discord_id, island_id)
                VALUES($1,$2)
                ON CONFLICT(discord_id, island_id)
                DO UPDATE SET visits=island_discoveries.visits+1, last_visited_at=NOW()
                """,
                discord_id,
                session["destination_island"],
            )
            dest = self.islands.get(session["destination_island"], {"name": session["destination_island"]})
            return True, f"Land ho! You arrived at **{dest['name']}**."

        # Chance to trigger one unresolved encounter per voyage tick.
        pending = await self.db.fetchrow(
            "SELECT * FROM ocean_encounter_log WHERE travel_session_id=$1 AND resolved=FALSE LIMIT 1",
            int(session["id"]),
        )
        if pending:
            encounter = self.encounter_by_id(pending["encounter_id"])
            name = encounter.get("name", pending["encounter_id"]) if encounter else pending["encounter_id"]
            return True, f"Voyage in progress. ETA: {seconds_left}s. Unresolved encounter: **{name}**. Use `/resolveencounter`."

        if self.encounters and random.random() < 0.45:
            encounter = self.roll_encounter()
            await self.db.execute(
                """
                INSERT INTO ocean_encounter_log(discord_id, travel_session_id, encounter_id, payload)
                VALUES($1,$2,$3,$4::jsonb)
                """,
                discord_id,
                int(session["id"]),
                encounter["id"],
                json.dumps(encounter),
            )
            return True, f"🌊 Encounter! **{encounter['name']}** — {encounter.get('description', '')}\nUse `/resolveencounter` to handle it."

        return True, f"Sailing safely. ETA: {seconds_left}s. The sea is calm for now."

    def encounter_by_id(self, encounter_id: str) -> dict[str, Any] | None:
        return next((e for e in self.encounters if e["id"] == encounter_id), None)

    def roll_encounter(self) -> dict[str, Any]:
        total = sum(int(e.get("weight", 1)) for e in self.encounters)
        pick = random.randint(1, max(1, total))
        running = 0
        for encounter in self.encounters:
            running += int(encounter.get("weight", 1))
            if pick <= running:
                return encounter
        return self.encounters[0]

    async def resolve_encounter(self, discord_id: int) -> tuple[bool, str]:
        session = await self.active_travel_session(discord_id)
        if not session:
            return False, "You are not currently sailing."
        log = await self.db.fetchrow(
            """
            SELECT * FROM ocean_encounter_log
            WHERE discord_id=$1 AND travel_session_id=$2 AND resolved=FALSE
            ORDER BY created_at ASC
            LIMIT 1
            """,
            discord_id,
            int(session["id"]),
        )
        if not log:
            return False, "No unresolved ocean encounter. Use `/voyage` to continue sailing."
        encounter = self.encounter_by_id(log["encounter_id"]) or dict(log["payload"] or {})
        ship = await self.db.fetchrow("SELECT * FROM player_ships WHERE id=$1", int(session["ship_id"]))
        damage = int(encounter.get("damage", 0))
        rewards = encounter.get("rewards", {}) or {}
        beli = int(rewards.get("beli", 0))
        item_lines: list[str] = []

        if damage > 0 and ship:
            mitigated = max(0, damage - int(ship["upgrade_level"] or 0) * 2)
            await self.db.execute(
                "UPDATE player_ships SET hull_hp=GREATEST(0, hull_hp-$2), updated_at=NOW() WHERE id=$1",
                int(ship["id"]),
                mitigated,
            )
        if beli > 0:
            await self.db.execute(
                "UPDATE players SET beli=beli+$2, updated_at=NOW() WHERE discord_id=$1",
                discord_id,
                beli,
            )
        inv = InventoryService(self.db)
        for item in rewards.get("items", []):
            await inv.add_item(discord_id, item["item_id"], int(item.get("quantity", 1)))
            item_lines.append(f"{item.get('quantity', 1)}x `{item['item_id']}`")
        await self.db.execute(
            "UPDATE ocean_encounter_log SET resolved=TRUE, resolved_at=NOW() WHERE id=$1",
            int(log["id"]),
        )
        parts = [f"Resolved **{encounter.get('name', log['encounter_id'])}**."]
        if damage:
            parts.append(f"Ship damage: {damage}.")
        if beli:
            parts.append(f"Beli gained: {beli:,}.")
        if item_lines:
            parts.append("Items: " + ", ".join(item_lines))
        return True, " ".join(parts)
