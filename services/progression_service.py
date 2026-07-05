from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.database import Database
from services.player_service import PlayerService

VALID_STATS = {"strength", "defense", "speed", "focus"}


class ProgressionService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def require_player(self, discord_id: int):
        return await PlayerService(self.db).get_player(discord_id)

    async def recover(self, discord_id: int) -> tuple[bool, str, dict[str, Any] | None]:
        player = await self.require_player(discord_id)
        if not player:
            return False, "Use `/start` first.", None

        restored_hp = int(player["max_hp"]) - int(player["hp"])
        restored_stamina = int(player["max_stamina"]) - int(player["stamina"])

        await self.db.execute(
            """
            UPDATE players
            SET hp=max_hp,
                stamina=max_stamina,
                last_recover=NOW(),
                updated_at=NOW()
            WHERE discord_id=$1
            """,
            discord_id,
        )
        return True, "You rested and recovered your strength.", {
            "restored_hp": restored_hp,
            "restored_stamina": restored_stamina,
        }

    async def claim_daily(self, discord_id: int) -> tuple[bool, str, dict[str, Any] | None]:
        player = await self.require_player(discord_id)
        if not player:
            return False, "Use `/start` first.", None

        last_daily = player.get("last_daily")
        now = datetime.now(timezone.utc)
        if last_daily:
            elapsed = now - last_daily
            if elapsed.total_seconds() < 20 * 60 * 60:
                remaining = int((20 * 60 * 60 - elapsed.total_seconds()) // 60)
                return False, f"Daily reward is not ready yet. Try again in about {remaining} minutes.", None
            streak = int(player.get("daily_streak", 0) or 0) + 1 if elapsed.total_seconds() < 48 * 60 * 60 else 1
        else:
            streak = 1

        streak_bonus = min(streak, 14)
        reward_beli = 350 + streak_bonus * 50
        reward_xp = 100 + streak_bonus * 15

        await self.db.execute(
            """
            UPDATE players
            SET beli=beli+$2,
                xp=xp+$3,
                daily_streak=$4,
                last_daily=NOW(),
                updated_at=NOW()
            WHERE discord_id=$1
            """,
            discord_id,
            reward_beli,
            reward_xp,
            streak,
        )
        await self.db.execute(
            """
            INSERT INTO daily_claims(discord_id, reward_xp, reward_beli, streak)
            VALUES($1, $2, $3, $4)
            """,
            discord_id,
            reward_xp,
            reward_beli,
            streak,
        )
        await self._level_check(discord_id)
        return True, "Daily reward claimed.", {"beli": reward_beli, "xp": reward_xp, "streak": streak}

    async def train(self, discord_id: int, stat_name: str) -> tuple[bool, str, dict[str, Any] | None]:
        stat_name = stat_name.lower().strip()
        if stat_name not in VALID_STATS:
            return False, "Choose one of: strength, defense, speed, focus.", None

        player = await self.require_player(discord_id)
        if not player:
            return False, "Use `/start` first.", None

        level = int(player["level"])
        current_stat = int(player.get(stat_name, 10) or 10)
        cost = 50 + level * 15 + current_stat * 5
        if int(player["beli"]) < cost:
            return False, f"You need {cost} Beli to train {stat_name}.", None

        xp_gain = 35 + level * 3
        stat_gain = 1
        await self.db.execute(
            f"""
            UPDATE players
            SET {stat_name}={stat_name}+$2,
                xp=xp+$3,
                beli=beli-$4,
                last_training=NOW(),
                updated_at=NOW()
            WHERE discord_id=$1
            """,
            discord_id,
            stat_gain,
            xp_gain,
            cost,
        )
        await self.db.execute(
            """
            INSERT INTO player_training_log(discord_id, stat_name, xp_gained, beli_spent)
            VALUES($1, $2, $3, $4)
            """,
            discord_id,
            stat_name,
            xp_gain,
            cost,
        )
        leveled = await self._level_check(discord_id)
        return True, f"Training complete: {stat_name.title()} increased.", {
            "stat": stat_name,
            "stat_gain": stat_gain,
            "xp": xp_gain,
            "cost": cost,
            "leveled": leveled,
        }

    async def leaderboard(self, board: str = "level"):
        board = board.lower().strip()
        if board not in {"level", "beli", "bounty", "wins"}:
            board = "level"
        order = {
            "level": "level DESC, xp DESC",
            "beli": "beli DESC, level DESC",
            "bounty": "bounty DESC, level DESC",
            "wins": "battles_won DESC, level DESC",
        }[board]
        return await self.db.fetch(f"""
            SELECT username, discord_id, level, xp, beli, bounty, battles_won
            FROM players
            ORDER BY {order}
            LIMIT 10
        """)

    async def _level_check(self, discord_id: int) -> bool:
        player = await self.require_player(discord_id)
        if not player:
            return False
        level = int(player["level"])
        xp = int(player["xp"])
        leveled = False
        while xp >= self.xp_needed(level):
            xp -= self.xp_needed(level)
            level += 1
            leveled = True
        if leveled:
            await self.db.execute(
                """
                UPDATE players
                SET level=$2,
                    xp=$3,
                    skill_points=skill_points+1,
                    max_hp=max_hp+10,
                    max_stamina=max_stamina+5,
                    hp=max_hp+10,
                    stamina=max_stamina+5,
                    updated_at=NOW()
                WHERE discord_id=$1
                """,
                discord_id,
                level,
                xp,
            )
        return leveled

    @staticmethod
    def xp_needed(level: int) -> int:
        return 150 + (level - 1) * 75
