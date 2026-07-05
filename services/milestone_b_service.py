import json
import os
import random
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str) -> Dict[str, Any]:
    with open(ROOT / path, "r", encoding="utf-8") as f:
        return json.load(f)


FRUITS = load_json("data/devil_fruits.json")
HAKI = load_json("data/haki_styles.json")
ENEMIES = load_json("data/milestone_b_enemies.json")


class MilestoneBService:
    def __init__(self, db):
        self.db = db

    async def init_schema(self):
        schema_path = ROOT / "sql" / "milestone_b_schema.sql"
        if schema_path.exists():
            await self.db.execute(schema_path.read_text(encoding="utf-8"))

    async def ensure_player_systems(self, discord_id: int):
        await self.db.execute(
            "INSERT INTO player_haki(player_id) VALUES($1) ON CONFLICT(player_id) DO NOTHING",
            discord_id,
        )
        await self.db.execute(
            "INSERT INTO player_fruits(player_id) VALUES($1) ON CONFLICT(player_id) DO NOTHING",
            discord_id,
        )

    async def get_player(self, discord_id: int):
        return await self.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", discord_id)

    async def get_haki(self, discord_id: int):
        await self.ensure_player_systems(discord_id)
        return await self.db.fetchrow("SELECT * FROM player_haki WHERE player_id=$1", discord_id)

    async def train_haki(self, discord_id: int, style: str) -> Tuple[bool, str]:
        style = style.lower()
        if style not in ("observation", "armament", "conqueror"):
            return False, "Unknown Haki style. Use observation, armament, or conqueror."
        player = await self.get_player(discord_id)
        if not player:
            return False, "Use -start first."
        if style == "conqueror" and int(player.get("level", 1)) < 35:
            return False, "Conqueror's Haki unlocks at level 35."
        await self.ensure_player_systems(discord_id)
        xp_gain = random.randint(14, 30)
        level_col = f"{style}_level"
        xp_col = f"{style}_xp"
        row = await self.get_haki(discord_id)
        new_xp = int(row[xp_col]) + xp_gain
        level = int(row[level_col])
        needed = 75 + level * 25
        leveled = False
        while new_xp >= needed and level < 100:
            new_xp -= needed
            level += 1
            needed = 75 + level * 25
            leveled = True
        await self.db.execute(
            f"UPDATE player_haki SET {level_col}=$1, {xp_col}=$2, updated_at=CURRENT_TIMESTAMP WHERE player_id=$3",
            level, new_xp, discord_id,
        )
        return True, f"{style.title()} Haki +{xp_gain} XP. Level {level}." + (" **LEVEL UP!**" if leveled else "")

    async def fruit_storage(self, discord_id: int):
        await self.ensure_player_systems(discord_id)
        return await self.db.fetch("SELECT * FROM fruit_storage WHERE player_id=$1 ORDER BY acquired_at DESC", discord_id)

    async def give_fruit(self, discord_id: int, fruit_id: str):
        if fruit_id not in FRUITS:
            return False, "Unknown fruit id."
        await self.db.execute("INSERT INTO fruit_storage(player_id, fruit_id) VALUES($1,$2)", discord_id, fruit_id)
        return True, f"Added {FRUITS[fruit_id]['name']} to storage."

    async def eat_fruit(self, discord_id: int, fruit_id: str):
        if fruit_id not in FRUITS:
            return False, "Unknown fruit id."
        await self.ensure_player_systems(discord_id)
        owned = await self.db.fetchrow("SELECT id FROM fruit_storage WHERE player_id=$1 AND fruit_id=$2 LIMIT 1", discord_id, fruit_id)
        if not owned:
            return False, "You don't have that fruit in storage."
        current = await self.db.fetchrow("SELECT equipped_fruit FROM player_fruits WHERE player_id=$1", discord_id)
        if current and current["equipped_fruit"]:
            return False, "You already ate a Devil Fruit. Use owner tools to reset during alpha."
        await self.db.execute("DELETE FROM fruit_storage WHERE id=$1", owned["id"])
        await self.db.execute("UPDATE player_fruits SET equipped_fruit=$1, fruit_mastery=1, fruit_xp=0 WHERE player_id=$2", fruit_id, discord_id)
        return True, f"You ate the **{FRUITS[fruit_id]['name']}**. Power flows through your body."

    async def fruit_profile(self, discord_id: int):
        await self.ensure_player_systems(discord_id)
        return await self.db.fetchrow("SELECT * FROM player_fruits WHERE player_id=$1", discord_id)

    async def find_fruit(self, discord_id: int):
        player = await self.get_player(discord_id)
        if not player:
            return False, "Use -start first."
        roll = random.random()
        if roll > 0.18:
            return False, "You searched the island but found no Devil Fruit."
        fruit_id = random.choices(list(FRUITS.keys()), weights=[18,4,4,8,14,1,1,1], k=1)[0]
        await self.give_fruit(discord_id, fruit_id)
        return True, f"You found a mysterious fruit: **{FRUITS[fruit_id]['name']}**!"

    async def start_battle(self, discord_id: int, enemy_id: str):
        if enemy_id not in ENEMIES:
            return False, "Unknown enemy."
        player = await self.get_player(discord_id)
        if not player:
            return False, "Use -start first."
        enemy = ENEMIES[enemy_id]
        await self.db.execute("DELETE FROM active_battles_v2 WHERE player_id=$1", discord_id)
        await self.db.execute(
            "INSERT INTO active_battles_v2(player_id, enemy_id, enemy_hp, player_hp) VALUES($1,$2,$3,$4)",
            discord_id, enemy_id, int(enemy["hp"]), int(player.get("hp", 100)),
        )
        return True, f"Battle started against **{enemy['name']}** — HP {enemy['hp']}."

    async def use_move(self, discord_id: int, move: str):
        battle = await self.db.fetchrow("SELECT * FROM active_battles_v2 WHERE player_id=$1", discord_id)
        if not battle:
            return False, "You are not in a Milestone B battle. Use -battle2 enemy_id."
        player = await self.get_player(discord_id)
        fruit = await self.fruit_profile(discord_id)
        haki = await self.get_haki(discord_id)
        enemy = ENEMIES[battle["enemy_id"]]
        base_attack = int(player.get("attack", 10)) + int(player.get("level", 1)) * 2
        stamina_cost = 0
        move_name = "Basic Strike"
        power = base_attack
        equipped = fruit["equipped_fruit"] if fruit else None
        if equipped and equipped in FRUITS:
            moves = FRUITS[equipped]["moves"]
            if move in moves:
                m = moves[move]
                move_name = m["name"]
                stamina_cost = int(m["stamina"])
                power = int(m["power"]) + int(fruit["fruit_mastery"]) * 2
        arm_bonus = int(haki["armament_level"]) * 0.8
        obs_bonus = int(haki["observation_level"]) * 0.03
        crit = random.random() < ((float(player.get("crit_chance", 5)) + obs_bonus) / 100)
        dmg = max(1, int(power + arm_bonus - int(enemy.get("defense", 0))))
        if crit:
            dmg = int(dmg * 1.7)
        enemy_hp = max(0, int(battle["enemy_hp"]) - dmg)
        enemy_hit = max(1, int(enemy["attack"]) - int(player.get("defense", 5)))
        dodged = random.random() < ((float(player.get("dodge_chance", 3)) + int(haki["observation_level"]) * 0.06) / 100)
        player_hp = int(battle["player_hp"])
        result = [f"You used **{move_name}** for **{dmg}** damage" + (" **CRIT!**" if crit else "")]
        if enemy_hp <= 0:
            await self.db.execute("DELETE FROM active_battles_v2 WHERE player_id=$1", discord_id)
            xp = int(enemy["xp"]); beli = int(enemy["beli"])
            await self.db.execute("UPDATE players SET xp=xp+$1, beli=beli+$2 WHERE discord_id=$3", xp, beli, discord_id)
            if equipped:
                await self.db.execute("UPDATE player_fruits SET fruit_xp=fruit_xp+$1 WHERE player_id=$2", max(5, dmg//3), discord_id)
            result.append(f"Victory! Gained **{xp} XP** and **{beli} Beli**.")
            return True, "\n".join(result)
        if dodged:
            result.append(f"{enemy['name']} attacked, but you dodged with Observation Haki instincts.")
        else:
            player_hp = max(0, player_hp - enemy_hit)
            result.append(f"{enemy['name']} hit you for **{enemy_hit}** damage. Your HP: {player_hp}")
        if player_hp <= 0:
            await self.db.execute("DELETE FROM active_battles_v2 WHERE player_id=$1", discord_id)
            await self.db.execute("UPDATE players SET hp=GREATEST(1, max_hp/2) WHERE discord_id=$1", discord_id)
            result.append("You were defeated and recovered at half HP.")
            return True, "\n".join(result)
        await self.db.execute("UPDATE active_battles_v2 SET enemy_hp=$1, player_hp=$2, turn_count=turn_count+1 WHERE player_id=$3", enemy_hp, player_hp, discord_id)
        result.append(f"Enemy HP: {enemy_hp}/{enemy['hp']}")
        return True, "\n".join(result)

    async def owner_log(self, owner_id: int, action: str, target_id: Optional[int], details: str):
        await self.db.execute("INSERT INTO owner_audit_log(owner_id, action, target_id, details) VALUES($1,$2,$3,$4)", owner_id, action, target_id, details)
