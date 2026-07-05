from __future__ import annotations

import os
import discord
from discord.ext import commands

from core.combat.battle_state import BattleState, Fighter
from core.combat.engine_v2 import hp_bar, hit_check, damage_roll, apply_status, tick_statuses
from core.fruits.registry import unlocked_moves, is_awakened
from core.haki.progression import VALID_HAKI, training_gain, dodge_bonus
from services.milestone_b_services import MilestoneBServices


OWNER_IDS = {
    int(x)
    for x in os.getenv("OWNER_IDS", "147462272544014336").replace(" ", "").split(",")
    if x
}


def owner_only():
    async def predicate(ctx):
        return ctx.author.id in OWNER_IDS
    return commands.check(predicate)


class MilestoneB(commands.Cog):
    """Milestone B Core: Fruit, Haki, Combat V2, Owner tools."""

    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "mb"):
            bot.mb = MilestoneBServices(bot.db)

    async def player(self, ctx) -> dict:
        return await self.bot.mb.ensure_player(ctx.author)

    @commands.group(name="mb", invoke_without_command=True)
    async def mb(self, ctx):
        await ctx.send(
            "**Milestone B Commands**\n"
            "`-mb haki`, `-mb trainhaki observation`, `-mb fruitdex`, `-mb fruitstorage`, "
            "`-mb eatfruit gomu_gomu`, `-mb fruitmoves`, `-mb battle mountain_bandit`, "
            "`-mb attack`, `-mb move gomu_pistol`, `-mb awakening`, `-mb selftest`"
        )

    @commands.group(name="mbowner", invoke_without_command=True)
    @owner_only()
    async def mbowner(self, ctx):
        await ctx.send(
            "`-mbowner givebeli @user amount`\n"
            "`-mbowner setlevel @user level`\n"
            "`-mbowner givefruit @user fruit_id`\n"
            "`-mbowner removefruit @user`"
        )

    @mbowner.command(name="givebeli")
    @owner_only()
    async def givebeli(self, ctx, member: discord.Member, amount: int):
        await self.bot.db.execute("UPDATE players SET beli=beli+$1 WHERE discord_id=$2", amount, member.id)
        await ctx.send(f"✅ Gave **{amount:,}** Beli to {member.mention}.")

    @mbowner.command(name="setlevel")
    @owner_only()
    async def setlevel(self, ctx, member: discord.Member, level: int):
        await self.bot.db.execute("UPDATE players SET level=$1 WHERE discord_id=$2", level, member.id)
        await ctx.send(f"✅ Set {member.mention} to level **{level}**.")

    @mbowner.command(name="givefruit")
    @owner_only()
    async def givefruit(self, ctx, member: discord.Member, fruit_id: str):
        fruit_id = fruit_id.lower()
        ok = await self.bot.mb.give_fruit(member.id, fruit_id)
        if not ok:
            return await ctx.send("Unknown fruit.")
        await ctx.send(f"🍈 Added **{fruit_id}** to {member.mention}'s fruit storage.")

    @mbowner.command(name="removefruit")
    @owner_only()
    async def removefruit(self, ctx, member: discord.Member):
        await self.bot.db.execute("UPDATE players SET fruit=NULL, fruit_mastery=0 WHERE discord_id=$1", member.id)
        await ctx.send(f"Removed Devil Fruit from {member.mention}.")

    @mb.command(name="haki")
    async def haki(self, ctx):
        p = await self.player(ctx)
        await ctx.send(
            f"👁 Observation: **{p['observation_haki']}**\n"
            f"🛡 Armament: **{p['armament_haki']}**\n"
            f"👑 Conqueror: **{p['conqueror_haki']}**"
        )

    @mb.command(name="trainhaki")
    async def trainhaki(self, ctx, style: str):
        style = style.lower()
        if style not in VALID_HAKI:
            return await ctx.send("Train: observation | armament | conqueror")

        p = await self.player(ctx)
        if p["stamina"] < 20:
            return await ctx.send("Not enough stamina. Use `-rest`.")

        col = f"{style}_haki"
        gain = training_gain(style)
        await self.bot.db.execute(
            f"UPDATE players SET {col}={col}+$1, stamina=GREATEST(0, stamina-20) WHERE discord_id=$2",
            gain,
            ctx.author.id,
        )
        await ctx.send(f"👑 Trained **{style.title()} Haki** (+{gain}).")

    @mb.command(name="fruitdex")
    async def fruitdex(self, ctx):
        embed = discord.Embed(title="🍈 Devil Fruit Encyclopedia", color=0xE67E22)
        for fruit in self.bot.mb.fruits.all():
            embed.add_field(
                name=f"{fruit.name} [{fruit.rarity}]",
                value=f"Element: {fruit.element}\nMoves: {len(fruit.moves)}\nAwakening: {fruit.awakening_level} mastery",
                inline=False,
            )
        await ctx.send(embed=embed)

    @mb.command(name="fruitstorage")
    async def fruitstorage(self, ctx):
        rows = await self.bot.db.fetch(
            "SELECT fruit_id FROM player_fruit_storage WHERE discord_id=$1 ORDER BY fruit_id",
            ctx.author.id,
        )
        if not rows:
            return await ctx.send("Your fruit storage is empty.")

        embed = discord.Embed(title="🍈 Fruit Storage", color=0xF39C12)
        for row in rows:
            fruit = self.bot.mb.fruits.get(row["fruit_id"])
            embed.add_field(
                name=fruit.name if fruit else row["fruit_id"],
                value=fruit.rarity if fruit else "Unknown",
                inline=False,
            )
        await ctx.send(embed=embed)

    @mb.command(name="eatfruit")
    async def eatfruit(self, ctx, fruit_id: str):
        await self.player(ctx)
        success, message = await self.bot.mb.eat_fruit(ctx.author.id, fruit_id.lower())
        await ctx.send(message)

    @mb.command(name="fruitmoves")
    async def fruitmoves(self, ctx):
        p = await self.player(ctx)
        if not p["fruit"]:
            return await ctx.send("No Devil Fruit equipped.")

        fruit = self.bot.mb.fruits.get(p["fruit"])
        moves = unlocked_moves(fruit, p["fruit_mastery"])
        if not moves:
            return await ctx.send("No moves unlocked.")

        await ctx.send(
            "\n".join(
                f"• **{m.name}** `-mb move {m.id}` • Power {m.power} • Stamina {m.stamina} • CD {m.cooldown}"
                for m in moves
            )
        )

    @mb.command(name="awakening")
    async def awakening(self, ctx):
        p = await self.player(ctx)
        if not p["fruit"]:
            return await ctx.send("No Devil Fruit equipped.")

        if is_awakened(p["fruit"], p["fruit_mastery"], self.bot.mb.fruits):
            await ctx.send("🌟 Your Devil Fruit is awakened.")
        else:
            await ctx.send("Your Devil Fruit is not awakened yet.")

    @mb.command(name="battle")
    async def battle(self, ctx, enemy_id: str = "mountain_bandit"):
        p = await self.player(ctx)
        if self.bot.mb.battles.get(ctx.author.id):
            return await ctx.send("You are already in battle.")

        enemy = self.bot.mb.enemies.create(enemy_id.lower())
        battle = BattleState(
            player=Fighter(
                id=ctx.author.id,
                name=ctx.author.display_name,
                hp=p["hp"],
                max_hp=p["max_hp"],
                stamina=p["stamina"],
                max_stamina=p["max_stamina"],
                attack=p["attack"],
                defense=p["defense"],
                speed=p["speed"],
                fruit=p["fruit"],
                fruit_mastery=p["fruit_mastery"],
                observation_haki=p["observation_haki"],
                armament_haki=p["armament_haki"],
                conqueror_haki=p["conqueror_haki"],
                dodge=0.02 + dodge_bonus(p["observation_haki"]),
            ),
            enemy=Fighter(
                id=-1,
                name=enemy.name,
                hp=enemy.hp,
                max_hp=enemy.hp,
                stamina=999,
                max_stamina=999,
                attack=enemy.attack,
                defense=enemy.defense,
                speed=enemy.speed,
            ),
            enemy_id=enemy.id,
        )
        self.bot.mb.battles.set(ctx.author.id, battle)
        await ctx.send(embed=self.battle_embed(battle))

    @mb.command(name="attack")
    async def attack(self, ctx):
        battle = self.bot.mb.battles.get(ctx.author.id)
        if not battle:
            return await ctx.send("Start a battle first with `-mb battle enemy_id`.")

        if hit_check(battle.player.accuracy, battle.enemy.dodge):
            dmg, crit = damage_roll(battle.player, battle.enemy)
            battle.damage(battle.player, battle.enemy, dmg)
            if crit:
                battle.log.append("💥 Critical hit!")
        else:
            battle.log.append("You missed.")

        await self.enemy_turn_or_finish(ctx, battle)

    @mb.command(name="move")
    async def move(self, ctx, move_id: str):
        battle = self.bot.mb.battles.get(ctx.author.id)
        if not battle:
            return await ctx.send("Start a battle first with `-mb battle enemy_id`.")

        p = await self.player(ctx)
        fruit = self.bot.mb.fruits.get(p["fruit"])
        if not fruit:
            return await ctx.send("No Devil Fruit equipped.")

        move = next(
            (m for m in unlocked_moves(fruit, p["fruit_mastery"]) if m.id == move_id.lower() or m.name.lower() == move_id.lower()),
            None,
        )
        if not move:
            return await ctx.send("Move locked or unknown.")

        if battle.player.stamina < move.stamina:
            return await ctx.send("Not enough stamina.")

        battle.player.stamina -= move.stamina
        dmg, crit = damage_roll(battle.player, battle.enemy, move.power)
        battle.damage(battle.player, battle.enemy, dmg)
        if crit:
            battle.log.append("💥 Critical hit!")
        if move.status:
            if apply_status(battle.enemy, move.status, move.status_turns, move.status_power):
                battle.log.append(f"{battle.enemy.name} is afflicted with {move.status}.")
        await self.enemy_turn_or_finish(ctx, battle)

    async def enemy_turn_or_finish(self, ctx, battle: BattleState):
        if battle.enemy.hp <= 0:
            enemy = self.bot.mb.enemies.create(battle.enemy_id)
            self.bot.mb.battles.clear(ctx.author.id)
            await self.bot.db.execute(
                """
                UPDATE players
                SET xp=xp+$1,
                    beli=beli+$2,
                    bounty=bounty+$3,
                    fruit_mastery=fruit_mastery+$4,
                    hp=$5,
                    stamina=$6
                WHERE discord_id=$7
                """,
                enemy.xp,
                enemy.beli,
                enemy.bounty,
                max(1, enemy.level // 2),
                battle.player.hp,
                battle.player.stamina,
                ctx.author.id,
            )
            return await ctx.send(
                f"🏆 Victory!\n+{enemy.xp} XP\n+{enemy.beli} Beli\n+{enemy.bounty} Bounty\n+{max(1, enemy.level // 2)} Fruit Mastery"
            )

        for line in tick_statuses(battle.player):
            battle.log.append(line)

        if hit_check(battle.enemy.accuracy, battle.player.dodge):
            dmg, _ = damage_roll(battle.enemy, battle.player)
            battle.damage(battle.enemy, battle.player, dmg)
        else:
            battle.log.append(f"{battle.enemy.name} missed.")

        battle.turn += 1
        await self.bot.db.execute(
            "UPDATE players SET hp=$1, stamina=$2 WHERE discord_id=$3",
            battle.player.hp,
            battle.player.stamina,
            ctx.author.id,
        )

        if battle.player.hp <= 0:
            self.bot.mb.battles.clear(ctx.author.id)
            return await ctx.send("💀 You were defeated.")

        await ctx.send(embed=self.battle_embed(battle))

    def battle_embed(self, battle: BattleState):
        embed = discord.Embed(title="⚔️ Battle V2", color=0xE74C3C)
        embed.add_field(
            name=battle.player.name,
            value=f"{hp_bar(battle.player.hp, battle.player.max_hp)}\n{battle.player.hp}/{battle.player.max_hp} HP\n{battle.player.stamina}/{battle.player.max_stamina} Stamina",
            inline=False,
        )
        embed.add_field(
            name=battle.enemy.name,
            value=f"{hp_bar(battle.enemy.hp, battle.enemy.max_hp)}\n{battle.enemy.hp}/{battle.enemy.max_hp} HP",
            inline=False,
        )
        if battle.log:
            embed.add_field(name="Log", value="\n".join(battle.log[-8:]), inline=False)
        return embed

    @mb.command(name="selftest")
    async def selftest(self, ctx):
        issues = []
        if not self.bot.mb.fruits.all():
            issues.append("No fruits loaded.")
        if not self.bot.mb.enemies.data:
            issues.append("No enemies loaded.")
        if issues:
            return await ctx.send("\n".join(f"❌ {x}" for x in issues))
        await ctx.send("✅ Milestone B systems loaded.")


async def setup(bot):
    await bot.add_cog(MilestoneB(bot))
