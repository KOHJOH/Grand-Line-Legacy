from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.player_service import PlayerService

class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="profile", description="View your character profile.")
    async def profile(self, interaction: discord.Interaction):
        service = PlayerService(self.bot.db)
        player = await service.get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        embed = discord.Embed(title=f"🏴‍☠️ {player['username']}", color=discord.Color.dark_gold())
        embed.add_field(name="Level", value=str(player["level"]))
        embed.add_field(name="XP", value=str(player["xp"]))
        embed.add_field(name="Beli", value=str(player["beli"]))
        embed.add_field(name="Race", value=player["race"])
        embed.add_field(name="Faction", value=player["faction"])
        embed.add_field(name="Island", value=player["current_island"])
        embed.add_field(name="HP", value=f"{player['hp']}/{player['max_hp']}")
        embed.add_field(name="Stamina", value=f"{player['stamina']}/{player['max_stamina']}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))
