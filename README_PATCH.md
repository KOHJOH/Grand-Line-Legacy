# Grand Line: Legacy Profile/Schema Patch

Replace these files in your GitHub repo:

- `cogs/profile.py`
- `sql/schema.sql`

Commit message:

`Fix profile missing race field and repair player schema`

Railway should redeploy automatically. The startup schema initializer will add missing player columns like `race`, `faction`, `title`, `bounty`, `crew_name`, and `devil_fruit`.

After redeploy, test:

1. `/start`
2. `/profile`

If `/profile` errors again, send the new Railway logs.
