from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from core.database import Database
from services.quest_service import QuestService
from services.reward_service import RewardService
from services.stat_service import StatService


class BattleService:
    def __init__(self, db: Database, game_data: Any) -> None:
        self.db = db
        self.game_data = game_data
        self.enemies = self._load_enemies()

    def _load_enemies(self) -> dict[str, dict[str, Any]]:
        path = Path("data/enemies.json")
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {enemy["id"]: enemy for enemy in data}

    async def get_active(self, discord_id: int):
        return await self.db.fetchrow(
            "SELECT * FROM npc_battle_sessions WHERE discord_id=$1 AND status='active' ORDER BY started_at DESC LIMIT 1",
            discord_id,
        )

    async def start(self, discord_id: int, enemy_id: str | None = None) -> tuple[bool, str, dict[str, Any] | None]:
        player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return False, "Use `/start` first.", None
        active = await self.get_active(discord_id)
        if active:
            enemy = self.enemies.get(active["enemy_id"], {"name": active["enemy_id"]})
            return False, f"You're already fighting **{enemy.get('name', active['enemy_id'])}**. Use `/battleaction`.", None
        if int(player["hp"]) <= 0:
            return False, "You're knocked out. Use `/rest` first.", None
        enemy = self._choose_enemy(player["current_island"], enemy_id)
        if not enemy:
            return False, "No enemies are available here yet.", None
        await self.db.execute(
            """
            INSERT INTO npc_battle_sessions(discord_id, enemy_id, enemy_hp, enemy_max_hp, turn, status, state)
            VALUES($1, $2, $3, $3, 1, 'active', '{}'::jsonb)
            """,
            discord_id,
            enemy["id"],
            int(enemy["hp"]),
        )
        return True, f"A wild **{enemy['name']}** appears!", enemy

    async def action(self, discord_id: int, action: str) -> tuple[bool, str, bool]:
        session = await self.get_active(discord_id)
        if not session:
            return False, "You are not in a battle. Use `/battle` first.", False
        player = await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)
        if not player:
            return False, "Use `/start` first.", False
        enemy = self.enemies.get(session["enemy_id"])
        if not enemy:
            await self.db.execute("UPDATE npc_battle_sessions SET status='ended', ended_at=NOW() WHERE id=$1", session["id"])
            return False, "Enemy data was missing, so the battle was cancelled.", True

        stats = await StatService(self.db, self.game_data).calculate(discord_id)
        if not stats:
            return False, "Stats could not be calculated.", False

        action = action.lower().strip()
        if action not in {"attack", "heavy", "defend", "flee"}:
            return False, "Action must be attack, heavy, defend, or flee.", False

        if action == "flee":
            if random.random() < 0.65:
                await self.db.execute("UPDATE npc_battle_sessions SET status='fled', ended_at=NOW() WHERE id=$1", session["id"])
                return True, "You escaped the battle.", True
            enemy_damage = self._enemy_damage(enemy, stats.defense, defending=False)
            await self._damage_player(discord_id, enemy_damage)
            return True, f"You failed to flee. **{enemy['name']}** hit you for **{enemy_damage}** damage.", False

        enemy_hp = int(session["enemy_hp"])
        defending = action == "defend"
        player_damage = 0
        player_text = ""

        if action == "defend":
            player_text = "You raised your guard."
        else:
            stamina_cost = 18 if action == "heavy" else 8
            if int(player["stamina"]) < stamina_cost:
                return False, "Not enough stamina. Use `defend` or `/rest`.", False
            await self.db.execute(
                "UPDATE players SET stamina=GREATEST(0, stamina-$2), updated_at=NOW() WHERE discord_id=$1",
                discord_id,
                stamina_cost,
            )
            multiplier = 1.65 if action == "heavy" else 1.0
            player_damage = self._player_damage(stats.attack, int(enemy.get("defense", 0)), stats.crit_chance, multiplier)
            enemy_hp = max(0, enemy_hp - player_damage)
            player_text = f"You used **{action.title()}** and dealt **{player_damage}** damage."

        if enemy_hp <= 0:
            rewards = enemy.get("rewards", {})
            reward_result = await RewardService(self.db, self.game_data).grant(discord_id, rewards)
            await QuestService(self.db, self.game_data).advance_kill(discord_id, enemy["id"])
            await self.db.execute(
                "UPDATE npc_battle_sessions SET enemy_hp=0, status='won', ended_at=NOW(), updated_at=NOW() WHERE id=$1",
                session["id"],
            )
            reward_text = self._format_rewards(reward_result)
            return True, f"{player_text}\n🏆 **{enemy['name']} defeated!**\n{reward_text}", True

        enemy_damage = self._enemy_damage(enemy, stats.defense, defending=defending)
        await self._damage_player(discord_id, enemy_damage)
        updated_player = await self.db.fetchrow("SELECT hp FROM players WHERE discord_id=$1", discord_id)
        if int(updated_player["hp"]) <= 0:
            await self.db.execute(
                "UPDATE npc_battle_sessions SET enemy_hp=$2, status='lost', ended_at=NOW(), updated_at=NOW() WHERE id=$1",
                session["id"],
                enemy_hp,
            )
            return True, f"{player_text}\n💀 **{enemy['name']}** hit you for **{enemy_damage}** damage. You were defeated.", True

        await self.db.execute(
            "UPDATE npc_battle_sessions SET enemy_hp=$2, turn=turn+1, updated_at=NOW() WHERE id=$1",
            session["id"],
            enemy_hp,
        )
        return True, f"{player_text}\n**{enemy['name']}** hit you for **{enemy_damage}** damage. Enemy HP: **{enemy_hp}/{enemy['hp']}**", False

    async def rest(self, discord_id: int) -> str:
        await self.db.execute(
            "UPDATE players SET hp=max_hp, stamina=max_stamina, updated_at=NOW() WHERE discord_id=$1",
            discord_id,
        )
        return "You rested and recovered your HP and stamina."

    def _choose_enemy(self, island: str, requested: str | None) -> dict[str, Any] | None:
        if requested:
            return self.enemies.get(requested)
        matches = [e for e in self.enemies.values() if island in e.get("islands", [])]
        if not matches:
            matches = list(self.enemies.values())
        if not matches:
            return None
        return random.choice(matches)

    def _player_damage(self, attack: int, enemy_defense: int, crit_chance: float, multiplier: float) -> int:
        base = max(1, int((attack * multiplier) - enemy_defense * 0.55))
        variance = random.randint(-2, 4)
        damage = max(1, base + variance)
        if random.random() < crit_chance / 100:
            damage = int(damage * 1.75)
        return damage

    def _enemy_damage(self, enemy: dict[str, Any], defense: int, defending: bool) -> int:
        base = max(1, int(enemy.get("attack", 5)) - int(defense * 0.45))
        damage = max(1, base + random.randint(-1, 3))
        if defending:
            damage = max(1, damage // 2)
        return damage

    async def _damage_player(self, discord_id: int, amount: int) -> None:
        await self.db.execute(
            "UPDATE players SET hp=GREATEST(0, hp-$2), updated_at=NOW() WHERE discord_id=$1",
            discord_id,
            amount,
        )

    def _format_rewards(self, rewards: dict[str, Any]) -> str:
        parts = []
        if rewards.get("xp"):
            parts.append(f"+{rewards['xp']} XP")
        if rewards.get("beli"):
            parts.append(f"+{rewards['beli']} Beli")
        for item_id, qty in (rewards.get("items") or {}).items():
            parts.append(f"+{qty} {item_id}")
        if rewards.get("leveled"):
            parts.append(f"LEVEL UP! Now level {rewards['level']}")
        return " • ".join(parts) if parts else "No rewards."
