from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.player_service import PlayerService

class StartCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="start", description="Create your Grand Line: Legacy character.")
    async def start(self, interaction: discord.Interaction):
        service = PlayerService(self.bot.db)
        player, created = await service.create_player(interaction.user.id, interaction.user.display_name)
        if created:
            msg = "🏴‍☠️ Character created. You woke up in Foosha Village with starter supplies."
        else:
            msg = "🏴‍☠️ Your character already exists. Welcome back."
        await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(StartCog(bot))
