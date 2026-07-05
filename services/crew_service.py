from __future__ import annotations

from typing import Any


class CrewService:
    def __init__(self, db):
        self.db = db

    async def get_player(self, discord_id: int):
        return await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)

    async def create_crew(self, owner_id: int, name: str):
        player = await self.get_player(owner_id)
        if not player:
            return None, "Use /start before creating a crew."
        existing_member = await self.db.fetchrow("SELECT * FROM crew_members WHERE discord_id=$1", owner_id)
        if existing_member:
            return None, "You are already in a crew. Leave/disband before creating another."
        existing = await self.db.fetchrow("SELECT * FROM crews WHERE lower(name)=lower($1)", name)
        if existing:
            return None, "A crew with that name already exists."
        crew = await self.db.fetchrow(
            """
            INSERT INTO crews (name, captain_id, level, xp, treasury, fame)
            VALUES ($1, $2, 1, 0, 0, 0)
            RETURNING *
            """,
            name[:40], owner_id,
        )
        await self.db.execute(
            "INSERT INTO crew_members (crew_id, discord_id, role) VALUES ($1, $2, 'Captain')",
            crew["id"], owner_id,
        )
        await self.db.execute("UPDATE players SET crew=$1 WHERE discord_id=$2", crew["name"], owner_id)
        return crew, None

    async def get_my_crew(self, discord_id: int):
        return await self.db.fetchrow(
            """
            SELECT c.*, cm.role FROM crews c
            JOIN crew_members cm ON cm.crew_id=c.id
            WHERE cm.discord_id=$1
            """, discord_id
        )

    async def add_member_by_id(self, captain_id: int, target_id: int):
        crew = await self.get_my_crew(captain_id)
        if not crew or crew["role"] != "Captain":
            return "Only a crew captain can recruit members."
        target = await self.get_player(target_id)
        if not target:
            return "That player has not used /start yet."
        existing = await self.db.fetchrow("SELECT * FROM crew_members WHERE discord_id=$1", target_id)
        if existing:
            return "That player is already in a crew."
        count = await self.db.fetchrow("SELECT COUNT(*) AS total FROM crew_members WHERE crew_id=$1", crew["id"])
        max_members = 10 + int(crew["level"]) * 2
        if count["total"] >= max_members:
            return f"Crew is full. Capacity: {max_members}."
        await self.db.execute("INSERT INTO crew_members (crew_id, discord_id, role) VALUES ($1,$2,'Member')", crew["id"], target_id)
        await self.db.execute("UPDATE players SET crew=$1 WHERE discord_id=$2", crew["name"], target_id)
        return f"Recruited <@{target_id}> into {crew['name']}."

    async def donate(self, discord_id: int, amount: int):
        if amount <= 0:
            return "Donation amount must be positive."
        crew = await self.get_my_crew(discord_id)
        if not crew:
            return "You are not in a crew."
        player = await self.get_player(discord_id)
        if int(player["beli"]) < amount:
            return "You don't have enough Beli."
        await self.db.execute("UPDATE players SET beli=beli-$1 WHERE discord_id=$2", amount, discord_id)
        await self.db.execute("UPDATE crews SET treasury=treasury+$1, xp=xp+$2, fame=fame+$2 WHERE id=$3", amount, max(1, amount//100), crew["id"])
        await self.try_level_crew(crew["id"])
        return f"Donated {amount:,} Beli to {crew['name']}."

    async def try_level_crew(self, crew_id: int):
        crew = await self.db.fetchrow("SELECT * FROM crews WHERE id=$1", crew_id)
        if not crew:
            return
        needed = int(crew["level"]) * 250
        if int(crew["xp"]) >= needed:
            await self.db.execute("UPDATE crews SET level=level+1, xp=xp-$1 WHERE id=$2", needed, crew_id)

    async def roster(self, discord_id: int):
        crew = await self.get_my_crew(discord_id)
        if not crew:
            return None, []
        members = await self.db.fetch(
            """
            SELECT cm.discord_id, cm.role, p.username, p.level
            FROM crew_members cm
            LEFT JOIN players p ON p.discord_id=cm.discord_id
            WHERE cm.crew_id=$1
            ORDER BY CASE cm.role WHEN 'Captain' THEN 0 ELSE 1 END, p.level DESC NULLS LAST
            """, crew["id"]
        )
        return crew, members
