import os
import discord
from discord.ext import commands
from services.milestone_b_service import MilestoneBService, FRUITS, ENEMIES


def is_owner(user_id: int) -> bool:
    owner = os.getenv("OWNER_ID", "").strip()
    return owner and str(user_id) == owner


def pick_mention_id(token: str):
    if not token:
        return None
    cleaned = token.replace("<@", "").replace("!", "").replace(">", "")
    return int(cleaned) if cleaned.isdigit() else None


class MilestoneBCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        db = getattr(self.bot, "db", None)
        if db:
            await MilestoneBService(db).init_schema()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.content.startswith("-"):
            return
        db = getattr(self.bot, "db", None)
        if db is None:
            return
        service = MilestoneBService(db)
        await service.init_schema()
        parts = message.content[1:].strip().split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]
        uid = message.author.id

        if cmd == "fruitdex":
            lines = ["🍈 **Devil Fruit Encyclopedia**"]
            for fid, fruit in FRUITS.items():
                lines.append(f"`{fid}` — **{fruit['name']}** [{fruit['rarity']} {fruit['type']}]")
            await message.reply("\n".join(lines[:25]))
            return

        if cmd == "fruitfind":
            ok, text = await service.find_fruit(uid)
            await message.reply(text)
            return

        if cmd == "fruitstorage":
            rows = await service.fruit_storage(uid)
            if not rows:
                await message.reply("Your fruit storage is empty. Use `-fruitfind` or owner tools.")
                return
            lines = ["📦 **Fruit Storage**"]
            for row in rows[:20]:
                fid = row["fruit_id"]
                lines.append(f"`{fid}` — {FRUITS.get(fid, {}).get('name', fid)}")
            await message.reply("\n".join(lines))
            return

        if cmd == "eatfruit":
            if not args:
                await message.reply("Use `-eatfruit fruit_id`.")
                return
            ok, text = await service.eat_fruit(uid, args[0])
            await message.reply(text)
            return

        if cmd == "fruitmoves":
            prof = await service.fruit_profile(uid)
            fid = prof["equipped_fruit"] if prof else None
            if not fid:
                await message.reply("You have not eaten a Devil Fruit.")
                return
            fruit = FRUITS[fid]
            lines = [f"🍈 **{fruit['name']} Moves**", f"Passive: {fruit['passive']}"]
            for mid, m in fruit["moves"].items():
                lines.append(f"`-move {mid}` — {m['name']} | Power {m['power']} | Stamina {m['stamina']}")
            await message.reply("\n".join(lines))
            return

        if cmd == "haki":
            row = await service.get_haki(uid)
            await message.reply(
                "👊 **Haki Progression**\n"
                f"Observation: Lv {row['observation_level']} XP {row['observation_xp']}\n"
                f"Armament: Lv {row['armament_level']} XP {row['armament_xp']}\n"
                f"Conqueror: Lv {row['conqueror_level']} XP {row['conqueror_xp']}"
            )
            return

        if cmd == "hakitrain":
            if not args:
                await message.reply("Use `-hakitrain observation`, `-hakitrain armament`, or `-hakitrain conqueror`.")
                return
            ok, text = await service.train_haki(uid, args[0])
            await message.reply(text)
            return

        if cmd == "battle2":
            enemy = args[0] if args else "bandit_bruiser"
            ok, text = await service.start_battle(uid, enemy)
            await message.reply(text)
            return

        if cmd in ("move", "attack2"):
            move = args[0] if args else "basic"
            ok, text = await service.use_move(uid, move)
            await message.reply(text)
            return

        if cmd == "enemylist":
            await message.reply("👹 **Enemies**\n" + "\n".join(f"`{eid}` — {e['name']} Lv {e['level']}" for eid,e in ENEMIES.items()))
            return

        if cmd == "owner":
            if not is_owner(uid):
                await message.reply("Owner only.")
                return
            sub = args[0].lower() if args else "help"
            if sub == "help":
                await message.reply(
                    "🛠️ **Owner Commands**\n"
                    "`-owner givebeli @user amount`\n"
                    "`-owner setlevel @user level`\n"
                    "`-owner givefruit @user fruit_id`\n"
                    "`-owner resetfruit @user`\n"
                    "`-owner spawnboss enemy_id`"
                )
                return
            if len(args) < 2 and sub != "spawnboss":
                await message.reply("Missing arguments. Use `-owner help`.")
                return
            if sub == "givebeli":
                target = pick_mention_id(args[1] if len(args)>1 else "")
                amount = int(args[2]) if len(args)>2 and args[2].isdigit() else 0
                await db.execute("UPDATE players SET beli=beli+$1 WHERE discord_id=$2", amount, target)
                await service.owner_log(uid, "givebeli", target, str(amount))
                await message.reply(f"Gave {amount} Beli to <@{target}>.")
                return
            if sub == "setlevel":
                target = pick_mention_id(args[1] if len(args)>1 else "")
                level = int(args[2]) if len(args)>2 and args[2].isdigit() else 1
                await db.execute("UPDATE players SET level=$1 WHERE discord_id=$2", level, target)
                await service.owner_log(uid, "setlevel", target, str(level))
                await message.reply(f"Set <@{target}> to level {level}.")
                return
            if sub == "givefruit":
                target = pick_mention_id(args[1] if len(args)>1 else "")
                fruit_id = args[2] if len(args)>2 else ""
                ok, text = await service.give_fruit(target, fruit_id)
                await service.owner_log(uid, "givefruit", target, fruit_id)
                await message.reply(text)
                return
            if sub == "resetfruit":
                target = pick_mention_id(args[1] if len(args)>1 else "")
                await db.execute("UPDATE player_fruits SET equipped_fruit=NULL, fruit_mastery=1, fruit_xp=0, awakened=FALSE WHERE player_id=$1", target)
                await service.owner_log(uid, "resetfruit", target, "")
                await message.reply(f"Reset fruit for <@{target}>.")
                return
            if sub == "spawnboss":
                enemy = args[1] if len(args)>1 else "axe_hand_morgan"
                if enemy not in ENEMIES:
                    await message.reply("Unknown enemy id.")
                else:
                    await service.owner_log(uid, "spawnboss", None, enemy)
                    await message.reply(f"Boss spawn announced: **{ENEMIES[enemy]['name']}**. Players can use `-battle2 {enemy}`.")
                return


async def setup(bot):
    await bot.add_cog(MilestoneBCog(bot))
