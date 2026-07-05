# Sprint 9 Command Conflict Patch

Fixes Railway startup crash:

- `CommandAlreadyRegistered: Command 'questboard' already registered.`
- Prevents the next likely duplicate `/rest` conflict.

## Replace these files

- `cogs/world.py`
- `cogs/battle.py`

## What changed

- Removed the old `/questboard` command from `cogs/world.py`.
  - The new quest system in `cogs/quests.py` owns `/questboard` now.
- Removed duplicate `/rest` from `cogs/battle.py`.
  - The existing boss combat cog already owns `/rest`.

## Commit message

`Fix duplicate questboard and rest command registration`

After Railway redeploys, test:

1. `/stats`
2. `/questboard`
3. `/queststart quest_id:foosha_training`
4. `/battle enemy_id:bandit_recruit`
5. `/battleaction action:attack`
