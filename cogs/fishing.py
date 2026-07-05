from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.fishing_service import FishingService


class FishingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="fish", description="Fish at your current island for resources and rare catches.")
    async def fish(self, interaction: discord.Interaction):
        player = await self.bot.db.fetchrow("SELECT current_island FROM players WHERE discord_id=$1", interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        result = await FishingService(self.bot.db).fish(interaction.user.id, player["current_island"])
        catch = result["catch"]
        embed = discord.Embed(title="🎣 Fishing Result", color=discord.Color.blue())
        embed.description = f"You caught **{catch.get('name', catch['item_id'])}** x{result['quantity']}!"
        embed.add_field(name="Rarity", value=catch.get("rarity", "Common"), inline=True)
        embed.add_field(name="XP", value=str(catch.get("xp", 5)), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="fishlog", description="View your latest fishing catches.")
    async def fishlog(self, interaction: discord.Interaction):
        rows = await self.bot.db.fetch(
            "SELECT * FROM fishing_log WHERE discord_id=$1 ORDER BY caught_at DESC LIMIT 10",
            interaction.user.id,
        )
        embed = discord.Embed(title="📘 Fishing Log", color=discord.Color.blue())
        if not rows:
            embed.description = "No catches yet. Use `/fish`."
        for row in rows:
            embed.add_field(name=row["item_id"], value=f"x{row['quantity']} at {row['island_id']}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FishingCog(bot))
