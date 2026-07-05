# Milestone B KeyError Fix

Railway failed loading `cogs.milestone_b` because `core/fruits/registry.py` required every JSON file in `data/fruits` to contain an `id`.

This patch updates the registry so:
- if a fruit JSON is missing `id`, it uses the filename as the fruit id
- malformed move objects are skipped instead of crashing the whole cog
- missing optional fruit fields get safe defaults

Replace:
- `core/fruits/registry.py`

Commit:
`Fix Milestone B fruit registry missing id crash`
