# Sprint 11 - Big MMO Progression Expansion

Replace/upload these folders/files into your GitHub repo, then commit:

`Sprint 11 - Crew achievements professions and bounty systems`

## Adds real systems

### Crew System
- `/crew`
- `/crewcreate`
- `/crewrecruit`
- `/crewdonate`
- Crew treasury, fame, XP, leveling, roster

### Achievement System
- `/achievements`
- `/claimcheck`
- Persistent achievement unlocks and rewards

### Profession System
- `/professions`
- `/gatherjob fishing|mining|foraging|cooking`
- Profession XP, profession leveling, item drops, Beli rewards

### Bounty System
- `/bounty`
- `/bountyleaderboard`
- `/addbounty` owner-only
- Persistent bounty logs

## New files
- `cogs/crew.py`
- `cogs/achievements.py`
- `cogs/professions.py`
- `cogs/bounty.py`
- `services/crew_service.py`
- `services/achievement_service.py`
- `services/profession_service.py`
- `services/bounty_service.py`
- `data/achievements.json`
- `sql/011_big_progression.sql`

## Modified
- `bot.py`

Railway should auto-run the SQL migration on startup because your database initializer loads every `sql/*.sql` file.
