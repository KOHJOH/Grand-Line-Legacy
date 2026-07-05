# Grand Line: Legacy — Real Sprint 4

Sprint 4 adds the first real Devil Fruit engine on top of Sprints 1–3.

## Included from earlier sprints
- `/start`, `/profile`
- `/inventory`, `/inspect`, `/use`, `/drop`, `/lockitem`
- `/equip`, `/unequip`, `/equipment`
- `/lootchest`, `/testbossloot`
- `/map`, `/travel`
- `/bosses`, `/bossfight`, `/bossaction`, `/bosscodex`, `/rest`
- PostgreSQL schema for players, inventory, equipment, loot, quests, boss codex, combat sessions

## New in Sprint 4 — Devil Fruits
Commands:
- `/fruitdex` — View FruitDex entries
- `/fruitfind` — Alpha test fruit search that adds a fruit item to inventory
- `/eatfruit fruit_id:<id>` — Eat a fruit item from inventory
- `/fruit` — View current fruit, mastery and abilities
- `/fruittrain` — Train fruit mastery
- `/fruitability ability_id:<id>` — Use an unlocked fruit ability
- `/awakenfruit` — Awaken eligible fruit at Mastery 100

Data:
- `data/fruits.json` contains 150 fruit definitions
- 55 fruits are marked awakenable
- Boss powers remain separate from player fruit ownership

Database additions:
- `fruit_registry`
- `player_fruits`
- `fruit_cooldowns`
- `fruitdex_entries`

## Setup
1. Create `.env` from `.env.example`.
2. Run `pip install -r requirements.txt`.
3. Run the full `sql/schema.sql` against PostgreSQL.
4. Start with `python bot.py`.

## Notes
This is still an alpha implementation. `/fruitfind` is intentionally generous for testing. Later the island/ocean spawn engine will replace the simple alpha search.
