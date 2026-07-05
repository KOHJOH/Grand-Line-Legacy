from __future__ import annotations

import random

ROUTES = {
    'foosha_village': ['shells_town', 'orange_town'],
    'shells_town': ['foosha_village', 'orange_town'],
    'orange_town': ['shells_town', 'syrup_village'],
    'syrup_village': ['orange_town', 'baratie'],
    'baratie': ['syrup_village', 'arlong_park'],
    'arlong_park': ['baratie', 'loguetown'],
    'loguetown': ['arlong_park'],
}

ENCOUNTERS = [
    ('marine_patrol', 'A Marine patrol cuts across your route.'),
    ('sea_king_shadow', 'A Sea King shadow moves beneath the waves.'),
    ('merchant_wreck', 'You spot wreckage from a merchant ship.'),
    ('storm_wall', 'A storm wall rolls over the horizon.'),
    ('pirate_scouts', 'Pirate scouts tail your ship from a distance.'),
]


def island_key(name: str) -> str:
    return name.lower().replace(' ', '_')


class SeaRouteService:
    def __init__(self, db) -> None:
        self.db = db

    async def routes_for_player(self, discord_id: int):
        row = await self.db.fetchrow('SELECT current_island FROM players WHERE discord_id=$1', discord_id)
        current = row['current_island'] if row else 'Foosha Village'
        return current, ROUTES.get(island_key(current), [])

    async def begin_voyage(self, discord_id: int, destination: str) -> tuple[bool, str]:
        player = await self.db.fetchrow('SELECT current_island FROM players WHERE discord_id=$1', discord_id)
        if not player:
            return False, 'Use `/start` first.'
        current_key = island_key(player['current_island'])
        dest_key = island_key(destination)
        if dest_key not in ROUTES.get(current_key, []):
            return False, 'That is not a direct sea route from your current island.'
        encounter_id, encounter_text = random.choice(ENCOUNTERS)
        await self.db.execute(
            '''INSERT INTO voyages(discord_id, origin, destination, encounter_id, status, created_at)
               VALUES($1,$2,$3,$4,'active',NOW())''',
            discord_id, player['current_island'], destination.replace('_',' ').title(), encounter_id,
        )
        return True, f"Voyage started toward **{destination.replace('_',' ').title()}**. Encounter: {encounter_text} Use `/voyageevent` to resolve it."

    async def resolve(self, discord_id: int) -> tuple[bool, str]:
        row = await self.db.fetchrow("SELECT * FROM voyages WHERE discord_id=$1 AND status='active' ORDER BY created_at DESC LIMIT 1", discord_id)
        if not row:
            return False, 'You do not have an active voyage.'
        xp = random.randint(15, 35)
        beli = random.randint(40, 120)
        await self.db.execute("UPDATE voyages SET status='completed', resolved_at=NOW() WHERE id=$1", row['id'])
        await self.db.execute('UPDATE players SET current_island=$2, xp=xp+$3, beli=beli+$4, updated_at=NOW() WHERE discord_id=$1', discord_id, row['destination'], xp, beli)
        return True, f"Voyage completed. You reached **{row['destination']}** and earned **{xp} XP** and **{beli} Beli**."
