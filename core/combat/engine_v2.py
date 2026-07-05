from __future__ import annotations

import random

IMMUNITIES = {
    "gomu_gomu": {"shock"},
    "mera_mera": {"burn"},
    "hie_hie": {"freeze"},
    "suna_suna": {"bleed"},
}


def hp_bar(current: int, maximum: int, size: int = 18) -> str:
    maximum = max(1, maximum)
    current = max(0, min(current, maximum))
    filled = int((current / maximum) * size)
    return "🟩" * filled + "⬛" * (size - filled)


def hit_check(accuracy: float, dodge: float) -> bool:
    chance = max(0.05, min(0.98, accuracy - dodge))
    return random.random() <= chance


def damage_roll(attacker, defender, power: int = 0) -> tuple[int, bool]:
    crit = random.random() <= getattr(attacker, "crit", 0.05)
    crit_mult = getattr(attacker, "crit_damage", 1.5) if crit else 1.0
    armament_bonus = getattr(attacker, "armament_haki", 0) / 800
    raw = (attacker.attack + power) * (1 + armament_bonus) * crit_mult
    return max(1, int(raw - defender.defense)), crit


def apply_status(target, status: str | None, turns: int, power: int) -> bool:
    if not status:
        return False
    if status in IMMUNITIES.get(target.fruit, set()):
        return False
    target.statuses.append({"status": status, "turns": turns, "power": power})
    return True


def tick_statuses(fighter) -> list[str]:
    lines: list[str] = []
    remaining: list[dict] = []
    for effect in fighter.statuses:
        status = effect["status"]
        turns = int(effect["turns"])
        power = int(effect["power"])
        if status in {"burn", "bleed", "poison", "shock", "freeze"}:
            fighter.hp = max(0, fighter.hp - power)
            lines.append(f"{fighter.name} took {power} {status} damage.")
        turns -= 1
        if turns > 0:
            effect["turns"] = turns
            remaining.append(effect)
    fighter.statuses = remaining
    return lines
