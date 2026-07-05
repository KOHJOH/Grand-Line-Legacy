# Milestone B - Real Systems Patch

Adds prefix-first Devil Fruit, Haki, combat expansion, and owner tools.

## Replace/Add files
- `cogs/milestone_b.py`
- `services/milestone_b_service.py`
- `data/devil_fruits.json`
- `data/haki_styles.json`
- `data/milestone_b_enemies.json`
- `sql/milestone_b_schema.sql`

## Required bot.py change
Add this cog to your extension list:

```py
"cogs.milestone_b",
```

## Test commands
```txt
-fruitdex
-fruitfind
-fruitstorage
-eatfruit gomu_gomu
-fruitmoves
-haki
-hakitrain observation
-hakitrain armament
-battle2 bandit_bruiser
-move pistol
-owner help
-owner givebeli @user 1000
-owner givefruit @user mera_mera
-owner setlevel @user 10
-owner spawnboss axe_hand_morgan
```

Owner commands require `OWNER_ID` in Railway variables.
