from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import logging


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
            logging.warning("Fruit data folder does not exist: %s", folder)
            return

        for file in root.glob("*.json"):
            try:
                raw = json.loads(file.read_text(encoding="utf-8"))
            except Exception:
                logging.exception("Failed to parse fruit JSON: %s", file)
                continue

            fruit_id = raw.get("id") or file.stem

            if "id" not in raw:
                logging.warning(
                    "Fruit file %s is missing 'id'; using filename '%s' as fruit id.",
                    file,
                    fruit_id,
                )

            moves = []
            for move in raw.get("moves", []):
                if "id" not in move:
                    logging.warning("Skipping fruit move missing id in %s: %s", file, move)
                    continue

                moves.append(
                    FruitMove(
                        id=move["id"],
                        name=move.get("name", move["id"].replace("_", " ").title()),
                        power=int(move.get("power", 1)),
                        stamina=int(move.get("stamina", 0)),
                        cooldown=int(move.get("cooldown", 0)),
                        unlock_mastery=int(move.get("unlock_mastery", 0)),
                        status=move.get("status"),
                        status_turns=int(move.get("status_turns", 0)),
                        status_power=int(move.get("status_power", 0)),
                    )
                )

            self.fruits[fruit_id] = DevilFruit(
                id=fruit_id,
                name=raw.get("name", fruit_id.replace("_", " ").title()),
                rarity=raw.get("rarity", "Common"),
                element=raw.get("element", "None"),
                awakening_level=int(raw.get("awakening_level", 500)),
                passive=raw.get("passive", {}),
                moves=moves,
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
