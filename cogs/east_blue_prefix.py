import json
from pathlib import Path
import random
import discord
from discord.ext import commands

BASE = Path(__file__).resolve().parent.parent / "data" / "east_blue"

def load_json(name):
    with open(BASE / name, "r", encoding="utf-8") as f:
        return json.load(f)

ISLANDS = load_json("islands.json")
ENEMIES = load_json("enemies.json")
QUESTS = load_json("quests.json")
SHOPS = load_json("shops.json")

class EastBluePrefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_prefix(self, msg, name):
        return msg.content.lower().startswith(f"-{name}")

    async def get_player(self, user_id):
        return await self.bot.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", user_id)

    async def cog_check(self, ctx):
        return True

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.content.startswith("-"):
            return
        ctx = await self.bot.get_context(message)
        content = message.content.strip()
        parts = content.split()
        cmd = parts[0][1:].lower()
        args = parts[1:]
        routes = {
            "eastblue": self.cmd_eastblue,
            "islands": self.cmd_islands,
            "travel": self.cmd_travel,
            "npcs": self.cmd_npcs,
            "talk": self.cmd_talk,
            "questboard": self.cmd_questboard,
            "queststart": self.cmd_queststart,
            "questturnin": self.cmd_questturnin,
            "battle": self.cmd_battle,
            "attack": self.cmd_attack,
            "shop": self.cmd_shop,
            "buy": self.cmd_buy,
        }
        if cmd in routes:
            await routes[cmd](ctx, args)

    async def cmd_eastblue(self, ctx, args):
        embed = discord.Embed(title="🌊 East Blue", description="Playable islands, quests, NPCs, shops, and enemy encounters.")
        for key, island in ISLANDS.items():
            embed.add_field(name=island["name"], value=f"Lv {island['level_min']} • {island['description']}", inline=False)
        await ctx.send(embed=embed)

    async def cmd_islands(self, ctx, args):
        p = await self.get_player(ctx.author.id)
        current = p["current_island"] if p else "foosha_village"
        embed = discord.Embed(title="🗺️ Islands", description=f"Current: **{current}**")
        for k, v in ISLANDS.items():
            embed.add_field(name=v["name"], value=f"Routes: {', '.join(v['routes']) or 'None'}", inline=False)
        await ctx.send(embed=embed)

    async def cmd_travel(self, ctx, args):
        if not args:
            return await ctx.send("Usage: `-travel shells_town`")
        dest = "_".join(args).lower().replace(" ", "_")
        if dest not in ISLANDS:
            return await ctx.send("Unknown island. Use `-islands`.")
        await self.bot.db.execute("UPDATE players SET current_island=$1 WHERE discord_id=$2", dest, ctx.author.id)
        await ctx.send(f"⛵ You sailed to **{ISLANDS[dest]['name']}**.")

    async def cmd_npcs(self, ctx, args):
        p = await self.get_player(ctx.author.id)
        current = p["current_island"] if p else "foosha_village"
        npcs = ISLANDS.get(current, ISLANDS["foosha_village"])["npcs"]
        await ctx.send("👥 NPCs here: " + ", ".join(f"`{n}`" for n in npcs))

    async def cmd_talk(self, ctx, args):
        npc = "_".join(args).lower() if args else ""
        lines = {
            "makino":"Keep your heart steady. Every legend starts with helping someone nearby.",
            "woop_slap":"Don't let your dreams turn you reckless, kid.",
            "rika":"The town needs real justice, not fear.",
            "chouchou":"Woof! The shop must be protected!",
            "zeff":"A hungry fighter is a weak fighter.",
            "genzo":"Freedom is worth fighting for.",
            "tashigi_swords":"A blade reveals the discipline of its wielder."
        }
        await ctx.send(f"💬 **{npc or 'NPC'}:** {lines.get(npc, 'They do not have dialogue yet, but they nod at your journey.')}")

    async def cmd_questboard(self, ctx, args):
        p = await self.get_player(ctx.author.id)
        current = p["current_island"] if p else "foosha_village"
        embed = discord.Embed(title="📜 Quest Board", description=f"Available at {ISLANDS.get(current, {}).get('name', current)}")
        for qid, q in QUESTS.items():
            if q["island"] == current:
                embed.add_field(name=f"{qid}: {q['title']}", value=f"{q['objective']} • Reward: {q['xp']} XP / {q['beli']} Beli", inline=False)
        await ctx.send(embed=embed)

    async def cmd_queststart(self, ctx, args):
        if not args:
            return await ctx.send("Usage: `-queststart foosha_001`")
        qid = args[0]
        q = QUESTS.get(qid)
        if not q:
            return await ctx.send("Unknown quest.")
        await self.bot.db.execute("INSERT INTO player_quests(discord_id, quest_id, required) VALUES($1,$2,$3) ON CONFLICT(discord_id, quest_id) DO NOTHING", ctx.author.id, qid, q["required"])
        await ctx.send(f"📜 Started **{q['title']}**\n💬 {q['dialogue']}")

    async def cmd_questturnin(self, ctx, args):
        if not args:
            return await ctx.send("Usage: `-questturnin foosha_001`")
        qid = args[0]
        q = QUESTS.get(qid)
        row = await self.bot.db.fetchrow("SELECT * FROM player_quests WHERE discord_id=$1 AND quest_id=$2", ctx.author.id, qid)
        if not q or not row:
            return await ctx.send("Quest not active.")
        if row["progress"] < row["required"]:
            return await ctx.send(f"Not done yet: {row['progress']}/{row['required']}.")
        await self.bot.db.execute("UPDATE player_quests SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE discord_id=$1 AND quest_id=$2", ctx.author.id, qid)
        await self.bot.db.execute("UPDATE players SET xp=xp+$1, beli=beli+$2 WHERE discord_id=$3", q["xp"], q["beli"], ctx.author.id)
        await ctx.send(f"🎁 Completed **{q['title']}**! +{q['xp']} XP, +{q['beli']} Beli")

    async def cmd_battle(self, ctx, args):
        enemy_id = args[0] if args else "mountain_bandit"
        e = ENEMIES.get(enemy_id)
        if not e:
            return await ctx.send("Unknown enemy.")
        player = await self.get_player(ctx.author.id)
        hp = player["hp"] if player else 100
        await self.bot.db.execute("INSERT INTO player_battles(discord_id, enemy_id, enemy_hp, player_hp) VALUES($1,$2,$3,$4) ON CONFLICT(discord_id) DO UPDATE SET enemy_id=$2, enemy_hp=$3, player_hp=$4, turn=1", ctx.author.id, enemy_id, e["hp"], hp)
        await ctx.send(f"⚔️ Battle started against **{e['name']}**! Enemy HP: {e['hp']}\nUse `-attack`.")

    async def cmd_attack(self, ctx, args):
        b = await self.bot.db.fetchrow("SELECT * FROM player_battles WHERE discord_id=$1", ctx.author.id)
        if not b:
            return await ctx.send("No active battle. Use `-battle mountain_bandit`.")
        e = ENEMIES[b["enemy_id"]]
        dmg = random.randint(12, 24)
        enemy_hp = max(0, b["enemy_hp"] - dmg)
        if enemy_hp <= 0:
            await self.bot.db.execute("DELETE FROM player_battles WHERE discord_id=$1", ctx.author.id)
            await self.bot.db.execute("UPDATE players SET xp=xp+$1, beli=beli+$2 WHERE discord_id=$3", e["xp"], e["beli"], ctx.author.id)
            # quest progress
            await self.bot.db.execute("UPDATE player_quests SET progress=LEAST(progress+1, required) WHERE discord_id=$1 AND status='active' AND quest_id IN (SELECT key FROM jsonb_each_text('{}'::jsonb))", ctx.author.id)
            for qid, q in QUESTS.items():
                if q.get("target") == b["enemy_id"]:
                    await self.bot.db.execute("UPDATE player_quests SET progress=LEAST(progress+1, required) WHERE discord_id=$1 AND quest_id=$2 AND status='active'", ctx.author.id, qid)
            return await ctx.send(f"🏆 Defeated **{e['name']}**! +{e['xp']} XP, +{e['beli']} Beli")
        retaliation = max(1, e["attack"] - random.randint(1, 8))
        player_hp = max(1, b["player_hp"] - retaliation)
        await self.bot.db.execute("UPDATE player_battles SET enemy_hp=$1, player_hp=$2, turn=turn+1 WHERE discord_id=$3", enemy_hp, player_hp, ctx.author.id)
        await ctx.send(f"🗡️ You dealt **{dmg}** damage. Enemy HP: **{enemy_hp}**\n💢 {e['name']} hit you for **{retaliation}**. Your battle HP: **{player_hp}**")

    async def cmd_shop(self, ctx, args):
        p = await self.get_player(ctx.author.id)
        current = p["current_island"] if p else "foosha_village"
        shop_id = ISLANDS[current]["shops"][0]
        embed = discord.Embed(title=f"🛒 {shop_id}")
        for item in SHOPS[shop_id]:
            embed.add_field(name=f"{item['id']} — {item['name']}", value=f"{item['price']} Beli", inline=False)
        await ctx.send(embed=embed)

    async def cmd_buy(self, ctx, args):
        if not args:
            return await ctx.send("Usage: `-buy wooden_sword`")
        item_id = args[0]
        p = await self.get_player(ctx.author.id)
        current = p["current_island"] if p else "foosha_village"
        shop_id = ISLANDS[current]["shops"][0]
        item = next((i for i in SHOPS[shop_id] if i["id"] == item_id), None)
        if not item:
            return await ctx.send("That item is not sold here.")
        if p["beli"] < item["price"]:
            return await ctx.send("Not enough Beli.")
        await self.bot.db.execute("UPDATE players SET beli=beli-$1 WHERE discord_id=$2", item["price"], ctx.author.id)
        await self.bot.db.execute("INSERT INTO player_inventory(discord_id, item_id, quantity) VALUES($1,$2,1) ON CONFLICT(discord_id, item_id) DO UPDATE SET quantity=player_inventory.quantity+1", ctx.author.id, item_id)
        await ctx.send(f"✅ Bought **{item['name']}**.")

async def setup(bot):
    await bot.add_cog(EastBluePrefix(bot))
