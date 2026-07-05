from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.progression_service import ProgressionService


class ProgressionCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="recover", description="Recover your HP and stamina outside of battle.")
    async def recover(self, interaction: discord.Interaction):
        ok, message, data = await ProgressionService(self.bot.db).recover(interaction.user.id)
        if not ok:
            await interaction.response.send_message("❌ " + message, ephemeral=True)
            return
        embed = discord.Embed(title="🛌 Recovery", description=message, color=discord.Color.blue())
        embed.add_field(name="HP Restored", value=str(data["restored_hp"]), inline=True)
        embed.add_field(name="Stamina Restored", value=str(data["restored_stamina"]), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="daily", description="Claim your daily login reward.")
    async def daily(self, interaction: discord.Interaction):
        ok, message, data = await ProgressionService(self.bot.db).claim_daily(interaction.user.id)
        if not ok:
            await interaction.response.send_message("❌ " + message, ephemeral=True)
            return
        embed = discord.Embed(title="🎁 Daily Reward", description=message, color=discord.Color.gold())
        embed.add_field(name="Beli", value=f"+{data['beli']}", inline=True)
        embed.add_field(name="XP", value=f"+{data['xp']}", inline=True)
        embed.add_field(name="Streak", value=f"{data['streak']} day(s)", inline=True)
        if data.get("leveled"):
            embed.set_footer(text="You leveled up! Check /profile or /stats.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="train", description="Train a core stat using Beli.")
    @app_commands.describe(stat="strength, defense, speed, or focus")
    async def train(self, interaction: discord.Interaction, stat: str):
        ok, message, data = await ProgressionService(self.bot.db).train(interaction.user.id, stat)
        if not ok:
            await interaction.response.send_message("❌ " + message, ephemeral=True)
            return
        embed = discord.Embed(title="🏋️ Training Complete", description=message, color=discord.Color.green())
        embed.add_field(name="Stat", value=data["stat"].title(), inline=True)
        embed.add_field(name="Gain", value=f"+{data['stat_gain']}", inline=True)
        embed.add_field(name="Cost", value=f"{data['cost']} Beli", inline=True)
        embed.add_field(name="XP", value=f"+{data['xp']}", inline=True)
        if data.get("leveled"):
            embed.set_footer(text="You leveled up and earned a skill point!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="View top pirates by level, Beli, bounty, or wins.")
    @app_commands.describe(board="level, beli, bounty, or wins")
    async def leaderboard(self, interaction: discord.Interaction, board: str = "level"):
        rows = await ProgressionService(self.bot.db).leaderboard(board)
        if not rows:
            await interaction.response.send_message("No players are ranked yet.", ephemeral=True)
            return
        lines = []
        for idx, row in enumerate(rows, start=1):
            metric = {
                "level": f"Lv.{row['level']} ({row['xp']} XP)",
                "beli": f"{row['beli']} Beli",
                "bounty": f"{row['bounty']} Bounty",
                "wins": f"{row['battles_won']} Wins",
            }.get(board.lower(), f"Lv.{row['level']}")
            lines.append(f"**#{idx}** {row['username']} — {metric}")
        embed = discord.Embed(title=f"🏆 Leaderboard: {board.title()}", description="\n".join(lines), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProgressionCog(bot))
