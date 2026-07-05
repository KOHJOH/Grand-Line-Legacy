# Grand Line: Legacy — Prefix Router Patch

## Why
Discord has a hard limit of 100 global slash commands. This patch adds unlimited text prefix commands using `-` while keeping the existing slash commands online.

## Replace/upload
- `bot.py`
- `cogs/prefix.py`

## Important
Message Content Intent must be enabled in the Discord Developer Portal. It is already enabled per the owner.

## Test
After Railway redeploys, test:

```txt
-help
-profile
-stats
-questboard
-queststart foosha_training
-battle bandit_recruit
-attack
-eastblue
-sailto orange_town
-crew
```

## Commit
```txt
Add prefix command router to bypass Discord slash command limit
```
