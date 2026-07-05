# Grand Line: Legacy — Milestone B Real Repo Patch

This patch is built for the current repo structure: `cogs/`, `core/`, `services/`, `data/`, and `sql/`.

## Adds

- `-mb` command group
- `-mbowner` owner/admin command group
- Combat V2
- Fruit registry
- Fruit storage/eating/moves
- Fruit mastery + awakening checks
- Haki training
- Enemy factory
- Milestone B SQL migration
- Updated `bot.py` with `cogs.milestone_b` added before `cogs.prefix`

## Test commands

```txt
-mb
-mb selftest
-mbowner givefruit @yourself gomu_gomu
-mb fruitstorage
-mb eatfruit gomu_gomu
-mb fruitmoves
-mb battle mountain_bandit
-mb attack
-mb move pistol
-mb haki
-mb trainhaki observation
-mb awakening
```

## Railway variable

```txt
OWNER_IDS=147462272544014336
```

## SQL

The schema additions are in:

```txt
sql/milestone_b.sql
```

If your startup only runs `sql/schema.sql`, copy the contents of `sql/milestone_b.sql` into the bottom of `sql/schema.sql`.
