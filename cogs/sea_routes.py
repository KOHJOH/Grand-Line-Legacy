from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.sea_route_service import SeaRouteService


class SeaRoutesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name='searoutes', description='View direct ocean routes from your island.')
    async def searoutes(self, interaction: discord.Interaction):
        current, routes = await SeaRouteService(self.bot.db).routes_for_player(interaction.user.id)
        route_text = '\n'.join(f'• `{r}`' for r in routes) or 'No direct routes.'
        await interaction.response.send_message(f'🌊 **Sea Routes from {current}**\n{route_text}', ephemeral=True)

    @app_commands.command(name='beginvoyage', description='Begin an ocean voyage to a connected island.')
    async def beginvoyage(self, interaction: discord.Interaction, destination: str):
        ok, msg = await SeaRouteService(self.bot.db).begin_voyage(interaction.user.id, destination)
        await interaction.response.send_message(('✅ ' if ok else '❌ ') + msg, ephemeral=True)

    @app_commands.command(name='voyageevent', description='Resolve your active ocean voyage encounter.')
    async def voyageevent(self, interaction: discord.Interaction):
        ok, msg = await SeaRouteService(self.bot.db).resolve(interaction.user.id)
        await interaction.response.send_message(('✅ ' if ok else '❌ ') + msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SeaRoutesCog(bot))
