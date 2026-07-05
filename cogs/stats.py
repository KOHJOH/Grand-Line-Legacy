from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.player_service import PlayerService
from services.stat_service import StatService


class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="stats", description="View your detailed combat stats.")
    async def stats(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return

        stats = await StatService(self.bot.db, self.bot.game_data).calculate(interaction.user.id)
        if not stats:
            await interaction.response.send_message("Could not calculate your stats.", ephemeral=True)
            return

        xp_bar = self._bar(stats.xp, stats.next_level_xp)
        embed = discord.Embed(title="📊 Combat Stats", color=discord.Color.blurple())
        embed.add_field(name="Level", value=f"{stats.level}", inline=True)
        embed.add_field(name="XP", value=f"{stats.xp}/{stats.next_level_xp}\n{xp_bar}", inline=False)
        embed.add_field(name="HP", value=f"{stats.hp}/{stats.max_hp}", inline=True)
        embed.add_field(name="Stamina", value=f"{stats.stamina}/{stats.max_stamina}", inline=True)
        embed.add_field(name="Attack", value=str(stats.attack), inline=True)
        embed.add_field(name="Defense", value=str(stats.defense), inline=True)
        embed.add_field(name="Speed", value=str(stats.speed), inline=True)
        embed.add_field(name="Crit", value=f"{stats.crit_chance:.1f}%", inline=True)
        embed.add_field(name="Dodge", value=f"{stats.dodge_chance:.1f}%", inline=True)
        embed.add_field(name="Fruit Power", value=str(stats.fruit_power), inline=True)
        embed.add_field(name="Haki Power", value=str(stats.haki_power), inline=True)
        embed.add_field(name="Bounty", value=f"{stats.bounty:,} Beli", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def _bar(self, value: int, total: int, size: int = 10) -> str:
        if total <= 0:
            return "▱" * size
        filled = max(0, min(size, int((value / total) * size)))
        return "▰" * filled + "▱" * (size - filled)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
