from __future__ import annotations

from typing import Any


def row_get(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        try:
            return row.get(key, default)
        except Exception:
            return default


def progress_bar(value: int, total: int, size: int = 10) -> str:
    if total <= 0:
        return "▱" * size
    filled = max(0, min(size, int((value / total) * size)))
    return "▰" * filled + "▱" * (size - filled)


def fmt_beli(amount: int) -> str:
    return f"{int(amount):,} Beli"
