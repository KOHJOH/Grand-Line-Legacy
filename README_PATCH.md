# Grand Line: Legacy — Cumulative Update Sprint 12–15

This is a larger cumulative drop built on top of the Sprint 9–11 bundle.

## Replace / upload these folders/files

- `bot.py`
- `cogs/`
- `services/`
- `data/`
- `sql/`
- `core/database.py`

## New systems

### Economy + Market
- `/market`
- `/marketlist`
- `/marketbuy`
- `/marketcancel`
- currency ledger
- player listing storage
- inventory removal/return on list/cancel
- seller payout on purchase

### Crafting
- `/recipes`
- `/craft`
- recipe data file
- crafting log
- ingredient removal/result item creation

### Fishing
- `/fish`
- `/fishlog`
- island-based fishing tables
- profession XP hook
- fishing log table

### Dungeons
- `/dungeonlist`
- `/enterdungeon`
- `/dungeonaction`
- dungeon rooms
- stamina cost
- room rewards/traps
- completion reward

### Raids
- `/raidboard`
- `/startraid`
- `/joinraid`
- raid lobby table
- party JSON storage

### World Progression
- `/unlocks`
- `/checkpoint`
- island unlock table
- respawn checkpoint table

### Ship Missions
- `/shipmission`
- stamina cost
- XP/Beli rewards
- ship mission log

### Owner Alpha Tools
- `/grantitem`
- `/grantbeli`

Requires `OWNER_ID` Railway variable for owner-only commands.

## Commit message

```txt
Cumulative update - Sprint 12 to 15 world economy crafting dungeons raids
```

## Test order after Railway redeploy

1. `/profile`
2. `/stats`
3. `/fish`
4. `/recipes`
5. `/grantitem item_id:cloth_scrap quantity:5` owner only
6. `/craft recipe_id:bandage_pack`
7. `/market`
8. `/dungeonlist`
9. `/enterdungeon dungeon_id:bandit_hideout`
10. `/dungeonaction`
11. `/raidboard`
12. `/shipmission`
