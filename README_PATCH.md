# Sprint 9 Real Gameplay Patch

Adds real gameplay code for:

- `/stats`
- `/questboard`
- `/quests`
- `/queststart`
- `/questturnin`
- `/questabandon`
- `/battle`
- `/battleaction`
- `/rest`

## Replace/upload these paths

- `bot.py`
- `core/database.py`
- `sql/schema.sql`
- `services/stat_service.py`
- `services/reward_service.py`
- `services/quest_service.py`
- `services/battle_service.py`
- `cogs/stats.py`
- `cogs/quests.py`
- `cogs/battle.py`
- `data/enemies.json`
- `data/quests.json`

## Commit message

`Sprint 9 - Stats Quests and NPC Battle Engine`

After Railway redeploys, test in this order:

1. `/profile`
2. `/stats`
3. `/questboard`
4. `/queststart quest_id:foosha_training`
5. `/battle enemy_id:bandit_recruit`
6. `/battleaction action:attack`
7. Repeat `/battleaction action:attack` until the enemy dies.
8. `/quests`
9. `/questturnin quest_id:foosha_training`
