from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.world_progression_service import WorldProgressionService


class WorldProgressionCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="unlocks", description="View islands you have unlocked.")
    async def unlocks(self, interaction: discord.Interaction):
        rows = await WorldProgressionService(self.bot.db).unlocked_islands(interaction.user.id)
        embed = discord.Embed(title="🗺️ Island Unlocks", color=discord.Color.green())
        if not rows:
            embed.description = "No unlock records yet. Foosha Village is your starting point."
        for row in rows:
            embed.add_field(name=row["island_id"], value=f"Reason: {row['reason']}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="checkpoint", description="Set your respawn checkpoint to your current island.")
    async def checkpoint(self, interaction: discord.Interaction):
        player = await self.bot.db.fetchrow("SELECT current_island FROM players WHERE discord_id=$1", interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        await WorldProgressionService(self.bot.db).set_checkpoint(interaction.user.id, player["current_island"])
        await interaction.response.send_message(f"✅ Checkpoint set to **{player['current_island']}**.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WorldProgressionCog(bot))
