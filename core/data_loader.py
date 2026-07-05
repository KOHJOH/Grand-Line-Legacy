from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class GameData:
    islands: list[dict[str, Any]]
    bosses: list[dict[str, Any]]
    quests: list[dict[str, Any]]
    items: list[dict[str, Any]]
    fruits: list[dict[str, Any]]
    loot_tables: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load_from_folder(cls, folder: str) -> "GameData":
        root = Path(folder)
        loot_root = root / "loot_tables"
        loot_tables: dict[str, dict[str, Any]] = {}
        if loot_root.exists():
            for path in loot_root.glob("*.json"):
                loot_tables[path.stem] = _load_json_any(path)
        return cls(
            islands=_load_json_list(root / "islands.json"),
            bosses=_load_json_list(root / "bosses.json"),
            quests=_load_json_list(root / "quests.json"),
            items=_load_json_list(root / "items.json"),
            fruits=_load_json_list(root / "fruits.json"),
            loot_tables=loot_tables,
        )


def _load_json_any(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    data = _load_json_any(path)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list")
    return data
