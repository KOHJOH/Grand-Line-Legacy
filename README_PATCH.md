# Grand Line: Legacy — Database Auto-Migration Patch

Replace these files in the repo:

- `bot.py`
- `core/database.py`

Keep your existing `sql/schema.sql` file.

What this does:
- Connects to PostgreSQL
- Runs `sql/schema.sql` automatically on startup
- Creates missing tables before `/start` or other commands can use them

Commit message:

`Fix database schema initialization`
