from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Fighter:
    id: int
    name: str
    hp: int
    max_hp: int
    stamina: int
    max_stamina: int
    attack: int
    defense: int
    speed: int
    fruit: str | None = None
    fruit_mastery: int = 0
    observation_haki: int = 0
    armament_haki: int = 0
    conqueror_haki: int = 0
    crit: float = 0.05
    crit_damage: float = 1.50
    dodge: float = 0.02
    accuracy: float = 0.95
    statuses: list[dict] = field(default_factory=list)


@dataclass
class BattleState:
    player: Fighter
    enemy: Fighter
    enemy_id: str
    turn: int = 1
    log: list[str] = field(default_factory=list)

    @property
    def done(self) -> bool:
        return self.player.hp <= 0 or self.enemy.hp <= 0

    def damage(self, attacker: Fighter, defender: Fighter, amount: int) -> None:
        amount = max(1, int(amount))
        defender.hp = max(0, defender.hp - amount)
        self.log.append(f"{attacker.name} dealt {amount} damage to {defender.name}.")
