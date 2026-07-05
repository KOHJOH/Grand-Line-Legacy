VALID_HAKI = {"observation", "armament", "conqueror"}


def training_gain(style: str) -> int:
    if style == "conqueror":
        return 1
    return 3


def dodge_bonus(observation: int) -> float:
    return observation / 1000


def armament_bonus(armament: int) -> float:
    return armament / 800
