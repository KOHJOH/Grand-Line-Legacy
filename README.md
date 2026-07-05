# Grand Line: Legacy — Real Sprint 5

Sprint 5 adds the first real Haki framework on top of Sprints 1–4.

## Included from earlier sprints
- `/start`, `/profile`
- `/inventory`, `/inspect`, `/use`, `/drop`, `/lockitem`
- `/equip`, `/unequip`, `/equipment`
- `/lootchest`, `/testbossloot`
- `/map`, `/travel`
- `/bosses`, `/bossfight`, `/bossaction`, `/bosscodex`, `/rest`
- `/fruitdex`, `/fruitfind`, `/eatfruit`, `/fruit`, `/fruittrain`, `/fruitability`, `/awakenfruit`
- PostgreSQL schema for players, inventory, equipment, loot, quests, boss codex, combat sessions, and fruits

## New in Sprint 5 — Haki Engine v1
Commands:
- `/haki` — View Observation, Armament, and Conqueror progression
- `/trainhaki haki_type:<observation|armament|conqueror>` — Train unlocked Haki using stamina
- `/observe` — Toggle Observation Haki bonuses
- `/coat` — Toggle Armament Haki coating bonuses
- `/conquer` — Toggle Conqueror's Haki pressure if awakened
- `/hakistats` — View exact active Haki combat modifiers

Data:
- `data/haki.json` contains Observation, Armament, and Conqueror progression data

Database additions:
- `player_haki`
- `haki_training_log`

Code additions:
- `services/haki_service.py`
- `cogs/haki.py`
- `bot.py` now loads `cogs.haki`

## Current Haki behavior
- Observation auto-unlocks at level 40.
- Armament auto-unlocks at level 60.
- Conqueror's Haki requires hidden potential before it can train.
- Haki training costs stamina and gives XP.
- Active Haki generates combat modifiers through `HakiService.combat_modifiers()`.

## Setup
1. Create `.env` from `.env.example`.
2. Run `pip install -r requirements.txt`.
3. Run the full `sql/schema.sql` against PostgreSQL.
4. Start with `python bot.py`.

## Git commit suggestion
`Sprint 5 - Haki Engine v1`

## Notes
This is Haki framework v1. Sprint 5.2 should wire these modifiers deeper into boss combat calculations and add Observation dodge / Armament damage-defense effects during actual turns.
