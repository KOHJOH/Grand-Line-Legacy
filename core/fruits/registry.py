from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(slots=True)
class FruitMove:
    id: str
    name: str
    power: int
    stamina: int
    cooldown: int
    unlock_mastery: int
    status: str | None = None
    status_turns: int = 0
    status_power: int = 0


@dataclass(slots=True)
class DevilFruit:
    id: str
    name: str
    rarity: str
    element: str
    awakening_level: int
    passive: dict
    moves: list[FruitMove]


class FruitRegistry:
    def __init__(self) -> None:
        self.fruits: dict[str, DevilFruit] = {}

    def load(self, folder: str = "data/fruits") -> None:
        root = Path(folder)
        if not root.exists():
            return
        for file in root.glob("*.json"):
            raw = json.loads(file.read_text(encoding="utf-8"))
            self.fruits[raw["id"]] = DevilFruit(
                id=raw["id"],
                name=raw["name"],
                rarity=raw.get("rarity", "Common"),
                element=raw.get("element", "None"),
                awakening_level=int(raw.get("awakening_level", 500)),
                passive=raw.get("passive", {}),
                moves=[FruitMove(**move) for move in raw.get("moves", [])],
            )

    def get(self, fruit_id: str | None) -> DevilFruit | None:
        if not fruit_id:
            return None
        return self.fruits.get(fruit_id)

    def all(self) -> list[DevilFruit]:
        return list(self.fruits.values())

    def exists(self, fruit_id: str) -> bool:
        return fruit_id in self.fruits


def unlocked_moves(fruit: DevilFruit, mastery: int) -> list[FruitMove]:
    return [move for move in fruit.moves if mastery >= move.unlock_mastery]


def is_awakened(fruit_id: str | None, mastery: int, registry: FruitRegistry) -> bool:
    fruit = registry.get(fruit_id)
    return bool(fruit and mastery >= fruit.awakening_level)
