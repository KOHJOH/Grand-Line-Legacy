from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from core.database import Database


@dataclass(slots=True)
class HakiResult:
    ok: bool
    title: str
    message: str


class HakiService:
    """Sprint 5 Haki progression and combat support service."""

    HAKI_TYPES = {"observation", "armament", "conqueror"}

    def __init__(self, db: Database, game_data: Any) -> None:
        self.db = db
        self.game_data = game_data
        self.haki_data = {h["id"]: h for h in getattr(game_data, "haki", [])}

    async def ensure_profile(self, discord_id: int) -> None:
        await self.db.execute(
            """
            INSERT INTO player_haki(discord_id)
            VALUES($1)
            ON CONFLICT(discord_id) DO NOTHING
            """,
            discord_id,
        )

    async def get_profile(self, discord_id: int):
        await self.ensure_profile(discord_id)
        return await self.db.fetchrow("SELECT * FROM player_haki WHERE discord_id=$1", discord_id)

    def get_haki_meta(self, haki_type: str) -> dict[str, Any] | None:
        return self.haki_data.get(haki_type)

    def tier_for(self, haki_type: str, level: int) -> str:
        meta = self.get_haki_meta(haki_type)
        if not meta:
            return "Unknown"
        tier_name = meta["tiers"][0]["name"]
        for tier in meta.get("tiers", []):
            if level >= int(tier["level"]):
                tier_name = tier["name"]
        return tier_name

    async def unlock_available(self, discord_id: int) -> HakiResult:
        player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return HakiResult(False, "No Character", "Use `/start` first.")
        await self.ensure_profile(discord_id)
        profile = await self.get_profile(discord_id)
        unlocked: list[str] = []
        for haki_type in ("observation", "armament"):
            meta = self.haki_data[haki_type]
            flag = f"{haki_type}_unlocked"
            if not profile[flag] and int(player["level"]) >= int(meta["unlock_level"]):
                await self.db.execute(
                    f"UPDATE player_haki SET {flag}=TRUE, updated_at=NOW() WHERE discord_id=$1",
                    discord_id,
                )
                unlocked.append(meta["name"])
        if unlocked:
            return HakiResult(True, "Haki Awakened", "Unlocked: " + ", ".join(unlocked))
        return HakiResult(True, "No New Unlocks", "No new Haki unlocks are available right now.")

    async def grant_conqueror_potential(self, discord_id: int, reason: str = "manual") -> None:
        await self.ensure_profile(discord_id)
        await self.db.execute(
            """
            UPDATE player_haki
            SET conqueror_potential=TRUE, conqueror_unlocked=TRUE, updated_at=NOW(),
                haki_history = haki_history || jsonb_build_array(jsonb_build_object('event','conqueror_potential','reason',$2,'at',NOW()))
            WHERE discord_id=$1
            """,
            discord_id,
            reason,
        )

    async def train(self, discord_id: int, haki_type: str) -> HakiResult:
        haki_type = haki_type.lower().strip()
        if haki_type not in self.HAKI_TYPES:
            return HakiResult(False, "Invalid Haki", "Use `observation`, `armament`, or `conqueror`.")
        player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return HakiResult(False, "No Character", "Use `/start` first.")
        await self.unlock_available(discord_id)
        profile = await self.get_profile(discord_id)
        meta = self.haki_data[haki_type]
        unlocked_flag = f"{haki_type}_unlocked"
        if not profile[unlocked_flag]:
            return HakiResult(False, "Locked", f"{meta['name']} unlocks at level {meta['unlock_level']}.")
        cost = int(meta.get("training_stamina_cost", 15))
        if int(player["stamina"]) < cost:
            return HakiResult(False, "Too Tired", f"You need {cost} stamina to train {meta['name']}.")
        level_col = f"{haki_type}_level"
        xp_col = f"{haki_type}_xp"
        level = int(profile[level_col])
        if level >= int(meta.get("max_level", 100)):
            return HakiResult(False, "Mastered", f"{meta['name']} is already at level 100.")
        xp_gain = random.randint(int(meta["training_xp_min"]), int(meta["training_xp_max"]))
        old_tier = self.tier_for(haki_type, level)
        xp = int(profile[xp_col]) + xp_gain
        levels_gained = 0
        while xp >= 100 and level < 100:
            xp -= 100
            level += 1
            levels_gained += 1
        new_tier = self.tier_for(haki_type, level)
        await self.db.execute(
            f"""
            UPDATE player_haki
            SET {level_col}=$2, {xp_col}=$3, updated_at=NOW()
            WHERE discord_id=$1
            """,
            discord_id,
            level,
            xp,
        )
        await self.db.execute(
            "UPDATE players SET stamina=GREATEST(0, stamina-$2), updated_at=NOW() WHERE discord_id=$1",
            discord_id,
            cost,
        )
        msg = f"You gained **{xp_gain} {meta['name']} XP**. Level: **{level}/100** ({xp}/100 XP)."
        if levels_gained:
            msg += f"\n🔥 Level increased by **{levels_gained}**."
        if new_tier != old_tier:
            msg += f"\n🌟 New tier: **{new_tier}**."
        return HakiResult(True, f"{meta['emoji']} Haki Training", msg)

    async def activate(self, discord_id: int, haki_type: str) -> HakiResult:
        haki_type = haki_type.lower().strip()
        if haki_type not in self.HAKI_TYPES:
            return HakiResult(False, "Invalid Haki", "Use `observation`, `armament`, or `conqueror`.")
        player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return HakiResult(False, "No Character", "Use `/start` first.")
        profile = await self.get_profile(discord_id)
        meta = self.haki_data[haki_type]
        if not profile[f"{haki_type}_unlocked"]:
            return HakiResult(False, "Locked", f"{meta['name']} is not unlocked yet.")
        level = int(profile[f"{haki_type}_level"])
        if level <= 0:
            return HakiResult(False, "Untrained", f"Train {meta['name']} at least once first.")
        active_col = f"active_{haki_type}"
        await self.db.execute(
            f"UPDATE player_haki SET {active_col}=NOT {active_col}, updated_at=NOW() WHERE discord_id=$1",
            discord_id,
        )
        refreshed = await self.get_profile(discord_id)
        state = "active" if refreshed[active_col] else "inactive"
        return HakiResult(True, meta["name"], f"{meta['emoji']} {meta['name']} is now **{state}**.")

    async def combat_modifiers(self, discord_id: int) -> dict[str, float | int | bool]:
        profile = await self.get_profile(discord_id)
        obs = int(profile["observation_level"])
        arm = int(profile["armament_level"])
        conq = int(profile["conqueror_level"])
        active_obs = bool(profile["active_observation"])
        active_arm = bool(profile["active_armament"])
        active_conq = bool(profile["active_conqueror"])
        return {
            "observation_level": obs,
            "armament_level": arm,
            "conqueror_level": conq,
            "dodge_bonus": (obs * 0.0015) if active_obs else 0.0,
            "crit_bonus": (obs * 0.0008) if active_obs else 0.0,
            "damage_bonus": (arm * 0.0035) if active_arm else 0.0,
            "defense_bonus": (arm * 0.003) if active_arm else 0.0,
            "pressure_bonus": (conq * 0.0025) if active_conq else 0.0,
            "active_observation": active_obs,
            "active_armament": active_arm,
            "active_conqueror": active_conq,
        }
