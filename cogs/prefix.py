from __future__ import annotations

import shlex
from typing import Any, Awaitable, Callable

import discord
from discord.ext import commands

from services.battle_service import BattleService
from services.quest_service import QuestService
from services.stat_service import StatService
from services.progression_service import ProgressionService
from services.crew_service import CrewService
from services.east_blue_service import EastBlueService

try:
    from services.npc_service import NPCService
except Exception:  # pragma: no cover - alpha modules may not exist in older deployments
    NPCService = None  # type: ignore
try:
    from services.skill_service import SkillService
except Exception:  # pragma: no cover
    SkillService = None  # type: ignore
try:
    from services.fruit_world_service import FruitWorldService
except Exception:  # pragma: no cover
    FruitWorldService = None  # type: ignore
try:
    from services.sea_route_service import SeaRouteService
except Exception:  # pragma: no cover
    SeaRouteService = None  # type: ignore

PREFIX = "-"


def bar(current: int, maximum: int, size: int = 12) -> str:
    maximum = max(1, maximum)
    filled = max(0, min(size, round((current / maximum) * size)))
    return "█" * filled + "░" * (size - filled)


def yesno(value: bool) -> str:
    return "✅" if value else "❌"


class PrefixCog(commands.Cog):
    """Unlimited text-command router for Grand Line: Legacy.

    Discord globally caps slash commands at 100. This cog keeps the polished slash
    commands we already have, but unlocks unlimited MMO actions through a simple
    prefix system: `-battle`, `-quests`, `-crew create`, etc.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.routes: dict[str, Callable[[discord.Message, list[str]], Awaitable[None]]] = {
            "help": self.cmd_help,
            "commands": self.cmd_help,
            "start": self.cmd_start,
            "profile": self.cmd_profile,
            "stats": self.cmd_stats,
            "inventory": self.cmd_inventory,
            "inv": self.cmd_inventory,
            "quests": self.cmd_quests,
            "quest": self.cmd_quests,
            "questboard": self.cmd_questboard,
            "queststart": self.cmd_queststart,
            "questaccept": self.cmd_queststart,
            "questturnin": self.cmd_questturnin,
            "questabandon": self.cmd_questabandon,
            "battle": self.cmd_battle,
            "fight": self.cmd_battle,
            "battleaction": self.cmd_battleaction,
            "attack": self.cmd_attack,
            "heavy": self.cmd_heavy,
            "defend": self.cmd_defend,
            "flee": self.cmd_flee,
            "daily": self.cmd_daily,
            "train": self.cmd_train,
            "recover": self.cmd_recover,
            "rest": self.cmd_recover,
            "leaderboard": self.cmd_leaderboard,
            "crew": self.cmd_crew,
            "crewcreate": self.cmd_crewcreate,
            "crewrecruit": self.cmd_crewrecruit,
            "crewdonate": self.cmd_crewdonate,
            "eastblue": self.cmd_eastblue,
            "map": self.cmd_eastblue,
            "sailto": self.cmd_sailto,
            "travelto": self.cmd_sailto,
            "checkpoints": self.cmd_checkpoints,
            "npcs": self.cmd_npcs,
            "talk": self.cmd_talk,
            "skills": self.cmd_skills,
            "skill": self.cmd_skill,
            "useskill": self.cmd_skill,
            "fruitspawns": self.cmd_fruitspawns,
            "fruitspawn": self.cmd_fruitspawns,
            "fruitsearch": self.cmd_fruitsearch,
            "searchfruit": self.cmd_fruitsearch,
            "routes": self.cmd_routes,
            "route": self.cmd_routes,
            "voyage": self.cmd_voyage,
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.content.startswith(PREFIX):
            return
        raw = message.content[len(PREFIX):].strip()
        if not raw:
            return
        try:
            parts = shlex.split(raw)
        except ValueError:
            await message.reply("I couldn't read that command. Check your quotes and try again.", mention_author=False)
            return
        if not parts:
            return
        command = parts[0].lower()
        args = parts[1:]
        handler = self.routes.get(command)
        if not handler:
            await message.reply(f"Unknown command: `{PREFIX}{command}`. Use `-help`.", mention_author=False)
            return
        try:
            await handler(message, args)
        except Exception as exc:
            await message.reply(f"⚠️ Command crashed: `{type(exc).__name__}: {exc}`\nSend the Railway logs if this repeats.", mention_author=False)
            raise

    async def require_player(self, message: discord.Message):
        row = await self.bot.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", message.author.id)
        if not row:
            await message.reply("Use `-start` first to create your character.", mention_author=False)
        return row

    async def cmd_help(self, message: discord.Message, args: list[str]) -> None:
        embed = discord.Embed(
            title="🏴‍☠️ Grand Line: Legacy Prefix Commands",
            description="Use `-` commands when Discord slash commands hit the 100-command limit.",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Core", value="`-start` `-profile` `-stats` `-inventory` `-daily` `-train strength` `-recover` `-leaderboard`", inline=False)
        embed.add_field(name="Quests", value="`-questboard` `-quests` `-queststart <id>` `-questturnin <id>` `-questabandon <id>`", inline=False)
        embed.add_field(name="Combat", value="`-battle [enemy_id]` `-attack` `-heavy` `-defend` `-flee` `-skills` `-skill <skill_id>`", inline=False)
        embed.add_field(name="World", value="`-eastblue` `-sailto <island>` `-checkpoints` `-npcs` `-talk <npc_id>` `-routes` `-voyage <route_id>`", inline=False)
        embed.add_field(name="Crew/Fruits", value="`-crew` `-crewcreate <name>` `-crewrecruit @user` `-crewdonate <amount>` `-fruitspawns` `-fruitsearch`", inline=False)
        await message.reply(embed=embed, mention_author=False)

    async def cmd_start(self, message: discord.Message, args: list[str]) -> None:
        existing = await self.bot.db.fetchrow("SELECT * FROM players WHERE discord_id=$1", message.author.id)
        if existing:
            await message.reply(f"✅ You already have a character, **{existing['username']}**. Use `-profile`.", mention_author=False)
            return
        await self.bot.db.execute(
            """
            INSERT INTO players(discord_id, username, level, xp, beli, current_island, hp, max_hp, stamina, max_stamina, race, title, crew, devil_fruit)
            VALUES($1,$2,1,0,500,'Foosha Village',100,100,100,100,'Human','Rookie','None','None')
            ON CONFLICT(discord_id) DO NOTHING
            """,
            message.author.id,
            message.author.display_name,
        )
        await message.reply("🌊 Character created. Welcome to **Grand Line: Legacy**. Use `-profile`.", mention_author=False)

    async def cmd_profile(self, message: discord.Message, args: list[str]) -> None:
        player = await self.require_player(message)
        if not player:
            return
        embed = discord.Embed(title=f"🏴‍☠️ {player['username']}", color=discord.Color.blue())
        embed.add_field(name="Level", value=str(player["level"]))
        embed.add_field(name="XP", value=str(player["xp"]))
        embed.add_field(name="Beli", value=f"{int(player['beli']):,}")
        embed.add_field(name="Race", value=str(player.get("race", "Human") if hasattr(player, "get") else player["race"]))
        embed.add_field(name="Island", value=str(player["current_island"]))
        embed.add_field(name="Crew", value=str(player.get("crew", "None") if hasattr(player, "get") else player["crew"]))
        embed.add_field(name="Devil Fruit", value=str(player.get("devil_fruit", "None") if hasattr(player, "get") else player["devil_fruit"]))
        embed.add_field(name="HP", value=f"{player['hp']}/{player['max_hp']}\n{bar(int(player['hp']), int(player['max_hp']))}", inline=False)
        embed.add_field(name="Stamina", value=f"{player['stamina']}/{player['max_stamina']}\n{bar(int(player['stamina']), int(player['max_stamina']))}", inline=False)
        await message.reply(embed=embed, mention_author=False)

    async def cmd_stats(self, message: discord.Message, args: list[str]) -> None:
        stats = await StatService(self.bot.db, self.bot.game_data).calculate(message.author.id)
        if not stats:
            await message.reply("Use `-start` first.", mention_author=False)
            return
        embed = discord.Embed(title="📊 Combat Stats", color=discord.Color.green())
        embed.add_field(name="Level", value=f"{stats.level} ({stats.xp}/{stats.next_level_xp} XP)")
        embed.add_field(name="HP", value=f"{stats.hp}/{stats.max_hp}\n{bar(stats.hp, stats.max_hp)}")
        embed.add_field(name="Stamina", value=f"{stats.stamina}/{stats.max_stamina}\n{bar(stats.stamina, stats.max_stamina)}")
        embed.add_field(name="Attack", value=str(stats.attack))
        embed.add_field(name="Defense", value=str(stats.defense))
        embed.add_field(name="Speed", value=str(stats.speed))
        embed.add_field(name="Crit", value=f"{stats.crit_chance:.1f}%")
        embed.add_field(name="Dodge", value=f"{stats.dodge_chance:.1f}%")
        embed.add_field(name="Fruit Power", value=str(stats.fruit_power))
        embed.add_field(name="Haki Power", value=str(stats.haki_power))
        embed.add_field(name="Bounty", value=f"{stats.bounty:,}")
        await message.reply(embed=embed, mention_author=False)

    async def cmd_inventory(self, message: discord.Message, args: list[str]) -> None:
        await self.require_player(message)
        rows = await self.bot.db.fetch("SELECT item_id, quantity FROM player_inventory WHERE discord_id=$1 ORDER BY item_id LIMIT 20", message.author.id)
        embed = discord.Embed(title="🎒 Inventory", color=discord.Color.dark_gold())
        if not rows:
            embed.description = "Your inventory is empty. Fight enemies, gather, fish, craft, or complete quests."
        else:
            embed.description = "\n".join(f"• `{r['item_id']}` x{r['quantity']}" for r in rows)
        await message.reply(embed=embed, mention_author=False)

    async def cmd_questboard(self, message: discord.Message, args: list[str]) -> None:
        quests = getattr(self.bot.game_data, "quests", []) if self.bot.game_data else []
        embed = discord.Embed(title="📜 Quest Board", description="Use `-queststart <id>` to accept.", color=discord.Color.purple())
        for quest in quests[:15]:
            reward = quest.get("rewards", {})
            embed.add_field(
                name=f"{quest.get('name', quest.get('id'))} `{quest.get('id')}`",
                value=f"{quest.get('summary', quest.get('description', 'No description.'))}\nRewards: {reward.get('xp', 0)} XP • {reward.get('beli', 0)} Beli",
                inline=False,
            )
        await message.reply(embed=embed, mention_author=False)

    async def cmd_quests(self, message: discord.Message, args: list[str]) -> None:
        await self.require_player(message)
        service = QuestService(self.bot.db, self.bot.game_data)
        active = await service.active_quests(message.author.id)
        completed = await service.completed_quests(message.author.id)
        embed = discord.Embed(title="📖 Quest Journal", color=discord.Color.purple())
        if active:
            lines = []
            for row in active[:10]:
                q = service.get_definition(row["quest_id"]) or {"name": row["quest_id"]}
                lines.append(f"• **{q.get('name', row['quest_id'])}** `{row['quest_id']}`")
            embed.add_field(name="Active", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Active", value="No active quests. Use `-questboard`.", inline=False)
        embed.add_field(name="Completed", value=str(len(completed)), inline=False)
        await message.reply(embed=embed, mention_author=False)

    async def cmd_queststart(self, message: discord.Message, args: list[str]) -> None:
        if not args:
            await message.reply("Usage: `-queststart <quest_id>`", mention_author=False)
            return
        ok, msg = await QuestService(self.bot.db, self.bot.game_data).start_quest(message.author.id, args[0])
        await message.reply(("✅ " if ok else "❌ ") + msg, mention_author=False)

    async def cmd_questturnin(self, message: discord.Message, args: list[str]) -> None:
        if not args:
            await message.reply("Usage: `-questturnin <quest_id>`", mention_author=False)
            return
        service = QuestService(self.bot.db, self.bot.game_data)
        if hasattr(service, "turn_in"):
            ok, msg = await service.turn_in(message.author.id, args[0])
        elif hasattr(service, "complete_quest"):
            ok, msg = await service.complete_quest(message.author.id, args[0])
        else:
            ok, msg = False, "Quest turn-in service is not available in this build yet."
        await message.reply(("✅ " if ok else "❌ ") + msg, mention_author=False)

    async def cmd_questabandon(self, message: discord.Message, args: list[str]) -> None:
        if not args:
            await message.reply("Usage: `-questabandon <quest_id>`", mention_author=False)
            return
        ok = await QuestService(self.bot.db, self.bot.game_data).abandon_quest(message.author.id, args[0])
        await message.reply("✅ Quest abandoned." if ok else "❌ No active quest found with that ID.", mention_author=False)

    async def cmd_battle(self, message: discord.Message, args: list[str]) -> None:
        ok, msg, enemy = await BattleService(self.bot.db, self.bot.game_data).start(message.author.id, args[0] if args else None)
        embed = discord.Embed(title="⚔️ Battle", description=msg, color=discord.Color.red() if ok else discord.Color.dark_red())
        if enemy:
            embed.add_field(name="Enemy", value=f"**{enemy.get('name')}**\nHP: {enemy.get('hp')} • ATK: {enemy.get('attack')} • DEF: {enemy.get('defense', 0)}")
            embed.add_field(name="Actions", value="`-attack` `-heavy` `-defend` `-flee`", inline=False)
        await message.reply(embed=embed, mention_author=False)

    async def cmd_battleaction(self, message: discord.Message, args: list[str]) -> None:
        if not args:
            await message.reply("Usage: `-battleaction attack|heavy|defend|flee`", mention_author=False)
            return
        ok, msg, ended = await BattleService(self.bot.db, self.bot.game_data).action(message.author.id, args[0])
        await message.reply(("⚔️ " if ok else "❌ ") + msg, mention_author=False)

    async def cmd_attack(self, message: discord.Message, args: list[str]) -> None:
        await self.cmd_battleaction(message, ["attack"])

    async def cmd_heavy(self, message: discord.Message, args: list[str]) -> None:
        await self.cmd_battleaction(message, ["heavy"])

    async def cmd_defend(self, message: discord.Message, args: list[str]) -> None:
        await self.cmd_battleaction(message, ["defend"])

    async def cmd_flee(self, message: discord.Message, args: list[str]) -> None:
        await self.cmd_battleaction(message, ["flee"])

    async def cmd_daily(self, message: discord.Message, args: list[str]) -> None:
        ok, msg, data = await ProgressionService(self.bot.db).claim_daily(message.author.id)
        detail = "" if not data else f"\n+{data['xp']} XP • +{data['beli']} Beli • Streak {data['streak']}"
        await message.reply(("✅ " if ok else "❌ ") + msg + detail, mention_author=False)

    async def cmd_train(self, message: discord.Message, args: list[str]) -> None:
        stat = args[0] if args else "strength"
        ok, msg, data = await ProgressionService(self.bot.db).train(message.author.id, stat)
        detail = "" if not data else f"\n+{data['stat_gain']} {data['stat']} • +{data['xp']} XP • -{data['cost']} Beli"
        await message.reply(("✅ " if ok else "❌ ") + msg + detail, mention_author=False)

    async def cmd_recover(self, message: discord.Message, args: list[str]) -> None:
        ok, msg, data = await ProgressionService(self.bot.db).recover(message.author.id)
        await message.reply(("✅ " if ok else "❌ ") + msg, mention_author=False)

    async def cmd_leaderboard(self, message: discord.Message, args: list[str]) -> None:
        board = args[0] if args else "level"
        rows = await ProgressionService(self.bot.db).leaderboard(board)
        embed = discord.Embed(title=f"🏆 Leaderboard: {board.title()}", color=discord.Color.gold())
        if rows:
            embed.description = "\n".join(f"**#{i}** {r['username']} • Lv {r['level']} • {int(r['beli']):,} Beli • {int(r['bounty']):,} bounty" for i, r in enumerate(rows, 1))
        else:
            embed.description = "No players yet."
        await message.reply(embed=embed, mention_author=False)

    async def cmd_crew(self, message: discord.Message, args: list[str]) -> None:
        if args and args[0].lower() == "create":
            await self.cmd_crewcreate(message, args[1:])
            return
        if args and args[0].lower() == "donate":
            await self.cmd_crewdonate(message, args[1:])
            return
        crew, members = await CrewService(self.bot.db).roster(message.author.id)
        if not crew:
            await message.reply("You are not in a crew. Use `-crewcreate <name>`.", mention_author=False)
            return
        embed = discord.Embed(title=f"👥 {crew['name']}", color=discord.Color.teal())
        embed.add_field(name="Level", value=str(crew["level"]))
        embed.add_field(name="Treasury", value=f"{int(crew['treasury']):,} Beli")
        embed.add_field(name="Fame", value=f"{int(crew['fame']):,}")
        embed.add_field(name="Roster", value="\n".join(f"• {m.get('username') or m['discord_id']} — {m['role']} (Lv {m.get('level') or '?'})" for m in members[:20]) or "No members", inline=False)
        await message.reply(embed=embed, mention_author=False)

    async def cmd_crewcreate(self, message: discord.Message, args: list[str]) -> None:
        if not args:
            await message.reply("Usage: `-crewcreate <crew name>`", mention_author=False)
            return
        crew, err = await CrewService(self.bot.db).create_crew(message.author.id, " ".join(args))
        await message.reply(f"✅ Crew created: **{crew['name']}**" if crew else f"❌ {err}", mention_author=False)

    async def cmd_crewrecruit(self, message: discord.Message, args: list[str]) -> None:
        if not message.mentions:
            await message.reply("Usage: `-crewrecruit @user`", mention_author=False)
            return
        msg = await CrewService(self.bot.db).add_member_by_id(message.author.id, message.mentions[0].id)
        await message.reply(msg, mention_author=False)

    async def cmd_crewdonate(self, message: discord.Message, args: list[str]) -> None:
        if not args or not args[0].isdigit():
            await message.reply("Usage: `-crewdonate <amount>`", mention_author=False)
            return
        msg = await CrewService(self.bot.db).donate(message.author.id, int(args[0]))
        await message.reply(msg, mention_author=False)

    async def cmd_eastblue(self, message: discord.Message, args: list[str]) -> None:
        islands, current, level = await EastBlueService(self.bot.db).map_embed_rows(message.author.id)
        embed = discord.Embed(title="🌊 East Blue", description=f"Level {level} • Current: **{current}**", color=discord.Color.blue())
        for island in islands[:20]:
            embed.add_field(name=f"{'📍' if island['name'].lower()==str(current).lower() else '🏝️'} {island['name']}", value=f"Lv {island.get('required_level',1)} • Cost {island.get('travel_cost',0)} Beli", inline=False)
        await message.reply(embed=embed, mention_author=False)

    async def cmd_sailto(self, message: discord.Message, args: list[str]) -> None:
        if not args:
            await message.reply("Usage: `-sailto <island>`", mention_author=False)
            return
        ok, msg = await EastBlueService(self.bot.db).travel(message.author.id, " ".join(args))
        await message.reply(("✅ " if ok else "❌ ") + msg, mention_author=False)

    async def cmd_checkpoints(self, message: discord.Message, args: list[str]) -> None:
        points = await EastBlueService(self.bot.db).checkpoints(message.author.id)
        await message.reply("🧭 **Checkpoints**\n" + ("\n".join(f"• {p.replace('_',' ').title()}" for p in points) or "None yet."), mention_author=False)

    async def cmd_npcs(self, message: discord.Message, args: list[str]) -> None:
        if NPCService is None:
            await message.reply("NPC service is not available in this build yet.", mention_author=False)
            return
        service = NPCService(self.bot.db)
        npcs = service.available_npcs(await EastBlueService(self.bot.db).get_player_location(message.author.id)) if hasattr(service, "available_npcs") else []
        embed = discord.Embed(title="👥 NPCs", color=discord.Color.blurple())
        embed.description = "\n".join(f"• **{n.get('name')}** `{n.get('id')}` — {n.get('role','NPC')}" for n in npcs[:20]) or "No NPCs here yet."
        await message.reply(embed=embed, mention_author=False)

    async def cmd_talk(self, message: discord.Message, args: list[str]) -> None:
        if not args:
            await message.reply("Usage: `-talk <npc_id>`", mention_author=False)
            return
        if NPCService is None:
            await message.reply("NPC service is not available in this build yet.", mention_author=False)
            return
        service = NPCService(self.bot.db)
        if hasattr(service, "talk"):
            text = await service.talk(message.author.id, args[0])
        else:
            text = "NPC dialogue is not wired in this build yet."
        await message.reply(text, mention_author=False)

    async def cmd_skills(self, message: discord.Message, args: list[str]) -> None:
        if SkillService is None:
            await message.reply("Skill service is not available in this build yet.", mention_author=False)
            return
        service = SkillService(self.bot.db)
        skills = await service.player_skills(message.author.id) if hasattr(service, "player_skills") else []
        embed = discord.Embed(title="✨ Skills", color=discord.Color.magenta())
        embed.description = "\n".join(f"• `{s.get('id')}` **{s.get('name')}**" for s in skills[:20]) or "No skills unlocked yet."
        await message.reply(embed=embed, mention_author=False)

    async def cmd_skill(self, message: discord.Message, args: list[str]) -> None:
        if not args:
            await message.reply("Usage: `-skill <skill_id>`", mention_author=False)
            return
        if SkillService is None:
            await message.reply("Skill service is not available in this build yet.", mention_author=False)
            return
        service = SkillService(self.bot.db)
        if hasattr(service, "use_skill"):
            ok, text = await service.use_skill(message.author.id, args[0])
        else:
            ok, text = False, "Skill usage is not wired in this build yet."
        await message.reply(("✅ " if ok else "❌ ") + text, mention_author=False)

    async def cmd_fruitspawns(self, message: discord.Message, args: list[str]) -> None:
        if FruitWorldService is None:
            await message.reply("Fruit world service is not available in this build yet.", mention_author=False)
            return
        service = FruitWorldService(self.bot.db)
        rows = await service.active_spawns() if hasattr(service, "active_spawns") else []
        embed = discord.Embed(title="🍈 Devil Fruit Spawns", color=discord.Color.green())
        embed.description = "\n".join(f"• `{r.get('fruit_id')}` at **{r.get('island_id')}**" for r in rows[:15]) or "No known fruit spawns right now."
        await message.reply(embed=embed, mention_author=False)

    async def cmd_fruitsearch(self, message: discord.Message, args: list[str]) -> None:
        if FruitWorldService is None:
            await message.reply("Fruit world service is not available in this build yet.", mention_author=False)
            return
        service = FruitWorldService(self.bot.db)
        if hasattr(service, "search_current_island"):
            ok, msg = await service.search_current_island(message.author.id)
        else:
            ok, msg = False, "Fruit search is not wired in this build yet."
        await message.reply(("✅ " if ok else "❌ ") + msg, mention_author=False)

    async def cmd_routes(self, message: discord.Message, args: list[str]) -> None:
        if SeaRouteService is None:
            await message.reply("Sea route service is not available in this build yet.", mention_author=False)
            return
        service = SeaRouteService(self.bot.db)
        routes = service.routes() if hasattr(service, "routes") else []
        embed = discord.Embed(title="🚢 Sea Routes", color=discord.Color.blue())
        embed.description = "\n".join(f"• `{r.get('id')}` **{r.get('from')} → {r.get('to')}**" for r in routes[:20]) or "No routes loaded yet."
        await message.reply(embed=embed, mention_author=False)

    async def cmd_voyage(self, message: discord.Message, args: list[str]) -> None:
        if not args:
            await message.reply("Usage: `-voyage <route_id>`", mention_author=False)
            return
        if SeaRouteService is None:
            await message.reply("Sea route service is not available in this build yet.", mention_author=False)
            return
        service = SeaRouteService(self.bot.db)
        if hasattr(service, "start_voyage"):
            ok, msg = await service.start_voyage(message.author.id, args[0])
        else:
            ok, msg = False, "Voyages are not wired in this build yet."
        await message.reply(("✅ " if ok else "❌ ") + msg, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PrefixCog(bot))
