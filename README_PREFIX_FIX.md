# Prefix `-mb` Unknown Command Fix

This fixes the duplicate message:

`Unknown command: -mb. Use -help.`

## Use

Drop `apply_prefix_mb_fix.py` into your repo root, then run:

```bash
python apply_prefix_mb_fix.py
```

It patches:

```txt
cogs/prefix.py
```

Commit:

```txt
Fix prefix router duplicate unknown command for mb
```
