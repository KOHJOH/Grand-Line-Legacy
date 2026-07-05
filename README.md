# Grand Line Legacy — Real Sprint 8

Sprint 8 adds the first real Ship + Ocean Travel module on top of the Sprint 7 codebase.

## Added

### Ships
- `/shipyard` — View available ships.
- `/buyship` — Buy or claim a ship. Starter Raft is free once.
- `/ship` — View owned ships and active ship stats.
- `/setship` — Set your active ship.
- `/repairship` — Repair active ship hull HP.
- `/upgradeship` — Upgrade speed, hull, or cargo.

### Ocean Travel
- `/oceanmap` — View known sea routes from current island.
- `/sail` — Start a timed voyage to a connected island.
- `/voyage` — Check voyage progress and discover random ocean encounters.
- `/resolveencounter` — Resolve the current ocean encounter.
- `/oceanencounters` — View configured ocean encounter templates.

### Data
- `data/ships.json`
- `data/ocean_encounters.json`
- Added ship repair/crafting resources to `data/items.json`.

### Database
New tables in `sql/schema.sql`:
- `player_ships`
- `ship_cargo`
- `travel_sessions`
- `ocean_encounter_log`

## Commit message

```txt
Sprint 8 - Ship and Ocean Travel Engine
```

## Quick test flow

1. `/start`
2. `/shipyard`
3. `/buyship raft`
4. `/ship`
5. `/oceanmap`
6. `/sail mt_colubo` or another connected island from your current location
7. `/voyage`
8. `/resolveencounter` if an encounter appears
9. `/voyage` after ETA expires to arrive

## Notes

This is the first playable version of sailing. Later sprints can add crew roles, ship combat, cannons, cargo trading, weather, and fleet battles without replacing this foundation.
