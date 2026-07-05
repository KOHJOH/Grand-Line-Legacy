# Grand Line: Legacy — Cumulative Sprint 16–20 Update

This is a larger cumulative gameplay update focused on turning East Blue into a playable progression region.

## New cogs
- `cogs/east_blue.py`
- `cogs/npcs.py`
- `cogs/skills.py`
- `cogs/fruit_world.py`
- `cogs/sea_routes.py`

## New services
- `services/east_blue_service.py`
- `services/npc_service.py`
- `services/skill_service.py`
- `services/fruit_world_service.py`
- `services/sea_route_service.py`

## New data
- `data/east_blue/islands.json`
- `data/east_blue/npcs.json`
- `data/skills/skills.json`
- `data/fruits/fruit_world.json`

## New commands
- `/eastblue`
- `/sailto`
- `/checkpoints`
- `/localnpcs`
- `/talkto`
- `/skills`
- `/learnskill`
- `/trainskill`
- `/fruitspawns`
- `/searchfruit`
- `/spawnfruit`
- `/searoutes`
- `/beginvoyage`
- `/voyageevent`

## Database additions
Adds tables for island discovery, NPC relationships, player skills, fruit spawns, voyages, and story flags. The startup schema runner will create these automatically on Railway redeploy.

## Commit message
`Cumulative update - Sprint 16 to 20 East Blue NPC skills fruit spawns sea routes`
