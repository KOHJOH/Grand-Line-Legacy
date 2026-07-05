from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from typing import Any

from core.database import Database
from services.equipment_service import EquipmentService
from services.item_service import ItemService
from services.loot_service import LootService
from services.quest_service import QuestService


@dataclass(slots=True)
class CombatResult:
    title: str
    description: str
    ended: bool = False


class CombatService:
    """Turn-based boss combat engine.

    Sprint 3 scope:
    - one active boss fight per player
    - player actions: attack, defend, focus, skill, flee, status
    - boss phases and ability rotation
    - XP/Beli/loot grant on win through LootService
    - boss codex update
    - boss-hunt quest progress hook
    """

    def __init__(self, db: Database, game_data: Any) -> None:
        self.db = db
        self.game_data = game_data
        self.item_service = ItemService(game_data)
        self.equipment_service = EquipmentService(db)
        self.loot_service = LootService(db, game_data)
        self.quest_service = QuestService(db)
        self.bosses = {boss["id"]: boss for boss in game_data.bosses}

    def get_boss(self, boss_id: str) -> dict[str, Any] | None:
        return self.bosses.get(boss_id)

    async def get_session(self, discord_id: int):
        return await self.db.fetchrow(
            """
            SELECT * FROM combat_sessions
            WHERE discord_id=$1 AND status='active'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            discord_id,
        )

    async def start_boss_fight(self, discord_id: int, boss_id: str) -> CombatResult:
        boss = self.get_boss(boss_id)
        if not boss:
            return CombatResult("Unknown Boss", f"No boss exists with id `{boss_id}`.", True)

        active = await self.get_session(discord_id)
        if active:
            return CombatResult(
                "Already Fighting",
                f"You're already fighting `{active['boss_id']}`. Use `/bossaction action:status` or `/bossaction action:flee`.",
                False,
            )

        player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return CombatResult("No Character", "Use `/start` first.", True)

        if player["hp"] <= 0:
            await self.db.execute(
                "UPDATE players SET hp=GREATEST(1, max_hp / 2), stamina=GREATEST(25, max_stamina / 2) WHERE discord_id=$1",
                discord_id,
            )

        max_hp = int(boss.get("hp", 1000))
        phase = 1
        state = {"defending": False, "focus": 0, "turn_log": []}
        await self.db.execute(
            """
            INSERT INTO combat_sessions(discord_id, boss_id, boss_hp, boss_max_hp, phase, turn, status, state)
            VALUES($1, $2, $3, $3, $4, 1, 'active', $5::jsonb)
            """,
            discord_id,
            boss_id,
            max_hp,
            phase,
            json.dumps(state),
        )
        return CombatResult(
            f"⚔️ Boss Fight Started: {boss['name']}",
            self._boss_intro(boss) + "\n\nUse `/bossaction action:attack` to begin.",
            False,
        )

    async def perform_action(self, discord_id: int, action: str) -> CombatResult:
        action = action.lower().strip()
        session = await self.get_session(discord_id)
        if not session:
            return CombatResult("No Active Fight", "You're not in a boss fight. Use `/bossfight` first.", True)

        boss = self.get_boss(session["boss_id"])
        if not boss:
            await self._end_session(session["id"], "error")
            return CombatResult("Combat Error", "Boss data is missing. Fight ended safely.", True)

        player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return CombatResult("No Character", "Use `/start` first.", True)

        state = dict(session["state"] or {})
        state.setdefault("defending", False)
        state.setdefault("focus", 0)
        state.setdefault("turn_log", [])

        if action == "status":
            return CombatResult(f"📊 {boss['name']} Status", self._status_text(player, session, boss, state), False)
        if action == "flee":
            if random.random() < 0.75:
                await self._end_session(session["id"], "fled")
                return CombatResult("🏃 Escaped", "You escaped the battle. No rewards gained.", True)
            boss_text = await self._boss_turn(discord_id, player, session, boss, state)
            await self._save_state(session["id"], state)
            return CombatResult("🏃 Failed Escape", "You failed to escape!\n\n" + boss_text, False)

        if player["hp"] <= 0:
            await self._end_session(session["id"], "lost")
            return CombatResult("💀 Defeated", "You were already downed. The fight has ended.", True)

        lines: list[str] = []
        boss_hp = int(session["boss_hp"])
        stamina_cost = 0

        if action == "attack":
            dmg, crit = await self._player_damage(player, boss, state, multiplier=1.0)
            boss_hp = max(0, boss_hp - dmg)
            lines.append(f"⚔️ You attacked **{boss['name']}** for **{dmg}** damage{' CRIT' if crit else ''}.")
        elif action == "skill":
            stamina_cost = 20
            if int(player["stamina"]) < stamina_cost:
                lines.append("⚠️ Not enough stamina for a skill. You used a basic attack instead.")
                dmg, crit = await self._player_damage(player, boss, state, multiplier=1.0)
            else:
                await self.db.execute(
                    "UPDATE players SET stamina=GREATEST(0, stamina-$2), updated_at=NOW() WHERE discord_id=$1",
                    discord_id,
                    stamina_cost,
                )
                dmg, crit = await self._player_damage(player, boss, state, multiplier=1.65)
            boss_hp = max(0, boss_hp - dmg)
            lines.append(f"💥 You used a heavy skill for **{dmg}** damage{' CRIT' if crit else ''}.")
        elif action == "defend":
            state["defending"] = True
            await self.db.execute(
                "UPDATE players SET stamina=LEAST(max_stamina, stamina+10), updated_at=NOW() WHERE discord_id=$1",
                discord_id,
            )
            lines.append("🛡️ You brace for impact and recover **10 stamina**.")
        elif action == "focus":
            state["focus"] = min(3, int(state.get("focus", 0)) + 1)
            await self.db.execute(
                "UPDATE players SET stamina=LEAST(max_stamina, stamina+15), updated_at=NOW() WHERE discord_id=$1",
                discord_id,
            )
            lines.append(f"👁️ You study the boss. Focus is now **{state['focus']}/3** and you recover **15 stamina**.")
        else:
            return CombatResult("Invalid Action", "Use `attack`, `skill`, `defend`, `focus`, `status`, or `flee`.", False)

        old_phase = int(session["phase"])
        new_phase = self._phase_for_boss_hp(boss_hp, int(session["boss_max_hp"]))
        if new_phase > old_phase:
            lines.append(self._phase_text(boss, new_phase))

        await self.db.execute(
            """
            UPDATE combat_sessions
            SET boss_hp=$2, phase=$3, turn=turn+1, state=$4::jsonb, updated_at=NOW()
            WHERE id=$1
            """,
            session["id"],
            boss_hp,
            new_phase,
            json.dumps(state),
        )

        if boss_hp <= 0:
            win_text = await self._win(discord_id, session, boss)
            return CombatResult(f"🏆 {boss['name']} Defeated", "\n".join(lines) + "\n\n" + win_text, True)

        refreshed_player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        refreshed_session = await self.db.fetchrow("SELECT * FROM combat_sessions WHERE id=$1", session["id"])
        boss_text = await self._boss_turn(discord_id, refreshed_player, refreshed_session, boss, state)
        await self._save_state(session["id"], state)

        after_player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        if after_player["hp"] <= 0:
            await self._end_session(session["id"], "lost")
            return CombatResult(f"💀 Defeated by {boss['name']}", "\n".join(lines) + "\n\n" + boss_text + "\n\nYou were downed.", True)

        return CombatResult(f"⚔️ Fighting {boss['name']}", "\n".join(lines) + "\n\n" + boss_text + "\n\n" + self._short_bars(after_player, refreshed_session), False)

    async def _player_damage(self, player: Any, boss: dict[str, Any], state: dict[str, Any], multiplier: float) -> tuple[int, bool]:
        equipment_stats = await self.equipment_service.total_stats(int(player["discord_id"]))
        weapon_attack = int(equipment_stats.get("attack", 0))
        level = int(player["level"])
        focus = int(state.get("focus", 0))
        base = 20 + level * 4 + weapon_attack * 2 + focus * 10
        variance = random.uniform(0.85, 1.15)
        crit_chance = 0.08 + focus * 0.04
        crit = random.random() < crit_chance
        damage = int(base * multiplier * variance * (1.75 if crit else 1.0))
        state["focus"] = 0 if multiplier > 1.0 else focus
        return max(1, damage), crit

    async def _boss_turn(self, discord_id: int, player: Any, session: Any, boss: dict[str, Any], state: dict[str, Any]) -> str:
        phase = int(session["phase"])
        level = int(boss.get("level", 1))
        ability = self._select_boss_ability(boss, phase, int(session["turn"]))
        base = 8 + level * 2 + phase * 12
        dmg = int(base * ability["multiplier"] * random.uniform(0.85, 1.15))
        if state.get("defending"):
            dmg = max(1, int(dmg * 0.45))
            state["defending"] = False
        await self.db.execute(
            "UPDATE players SET hp=GREATEST(0, hp-$2), updated_at=NOW() WHERE discord_id=$1",
            discord_id,
            dmg,
        )
        return f"👑 **{boss['name']}** used **{ability['name']}** and dealt **{dmg}** damage."

    def _select_boss_ability(self, boss: dict[str, Any], phase: int, turn: int) -> dict[str, Any]:
        abilities = boss.get("abilities") or self._default_abilities_for(boss)
        unlocked = [a for a in abilities if int(a.get("phase", 1)) <= phase]
        if not unlocked:
            unlocked = self._default_abilities_for(boss)
        return unlocked[(turn - 1) % len(unlocked)]

    def _default_abilities_for(self, boss: dict[str, Any]) -> list[dict[str, Any]]:
        boss_type = str(boss.get("type", "Boss")).lower()
        if "marine" in boss_type:
            names = ["Justice Strike", "Reinforcement Rush", "Iron Discipline"]
        elif "beast" in boss_type or "sea" in boss_type:
            names = ["Savage Bite", "Crushing Slam", "Terrifying Roar"]
        elif "pirate" in boss_type or "bandit" in boss_type:
            names = ["Dirty Slash", "Ambush Combo", "Captain's Rage"]
        else:
            names = ["Heavy Strike", "Pressure Wave", "Finisher"]
        return [
            {"name": names[0], "multiplier": 1.0, "phase": 1},
            {"name": names[1], "multiplier": 1.25, "phase": 2},
            {"name": names[2], "multiplier": 1.55, "phase": 3},
        ]

    def _phase_for_boss_hp(self, boss_hp: int, boss_max_hp: int) -> int:
        ratio = boss_hp / max(1, boss_max_hp)
        if ratio <= 0.25:
            return 3
        if ratio <= 0.55:
            return 2
        return 1

    def _phase_text(self, boss: dict[str, Any], phase: int) -> str:
        if phase == 2:
            return f"\n🔥 **{boss['name']} enters Phase 2!** The fight becomes more dangerous."
        if phase == 3:
            return f"\n💀 **{boss['name']} enters Final Phase!** Their strongest attacks are unlocked."
        return ""

    async def _win(self, discord_id: int, session: Any, boss: dict[str, Any]) -> str:
        await self._end_session(session["id"], "won")
        boss_id = boss["id"]
        await self.db.execute(
            """
            INSERT INTO boss_codex(discord_id, boss_id, defeats, first_defeated_at, last_defeated_at)
            VALUES($1, $2, 1, NOW(), NOW())
            ON CONFLICT(discord_id, boss_id)
            DO UPDATE SET defeats = boss_codex.defeats + 1, last_defeated_at = NOW()
            """,
            discord_id,
            boss_id,
        )
        await self.quest_service.advance_boss_kill(discord_id, boss_id)
        rewards = await self.loot_service.roll_boss(discord_id, boss_id)
        items = rewards.get("items", [])
        item_lines = [f"• {self.item_service.display_name(i['item_id'])} x{i.get('quantity', 1)}" for i in items]
        if not item_lines:
            item_lines = ["• No item drops this time."]
        return (
            f"✨ XP: **{rewards.get('xp', 0)}**\n"
            f"💰 Beli: **{rewards.get('beli', 0)}**\n"
            f"🎁 Drops:\n" + "\n".join(item_lines)
        )

    async def _end_session(self, session_id: int, status: str) -> None:
        await self.db.execute(
            "UPDATE combat_sessions SET status=$2, ended_at=NOW(), updated_at=NOW() WHERE id=$1",
            session_id,
            status,
        )

    async def _save_state(self, session_id: int, state: dict[str, Any]) -> None:
        await self.db.execute("UPDATE combat_sessions SET state=$2::jsonb, updated_at=NOW() WHERE id=$1", session_id, json.dumps(state))

    def _boss_intro(self, boss: dict[str, Any]) -> str:
        return boss.get("intro") or f"**{boss['name']}** steps forward. The battle begins."

    def _status_text(self, player: Any, session: Any, boss: dict[str, Any], state: dict[str, Any]) -> str:
        return (
            f"**Player** HP: {player['hp']}/{player['max_hp']} | Stamina: {player['stamina']}/{player['max_stamina']}\n"
            f"**Boss** HP: {session['boss_hp']}/{session['boss_max_hp']} | Phase: {session['phase']}\n"
            f"Focus: {state.get('focus', 0)}/3"
        )

    def _short_bars(self, player: Any, session: Any) -> str:
        return (
            f"`Your HP {player['hp']}/{player['max_hp']} | Stamina {player['stamina']}/{player['max_stamina']}`\n"
            f"`Boss HP {session['boss_hp']}/{session['boss_max_hp']} | Phase {session['phase']}`"
        )
