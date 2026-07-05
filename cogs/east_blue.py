from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.east_blue_service import EastBlueService


class EastBlueCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name='eastblue', description='View your East Blue progression map.')
    async def eastblue(self, interaction: discord.Interaction):
        islands, current, level = await EastBlueService(self.bot.db).map_embed_rows(interaction.user.id)
        embed = discord.Embed(title='🌊 East Blue Map', description=f'Level {level} • Current: **{current}**', color=discord.Color.blue())
        for island in islands[:15]:
            embed.add_field(
                name=f"{'📍 ' if island['name'].lower()==current.lower() else '🏝️ '}{island['name']}",
                value=f"Lv. {island.get('required_level',1)} • {island.get('summary','')}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='sailto', description='Travel directly to an unlocked East Blue island.')
    async def sailto(self, interaction: discord.Interaction, island: str):
        ok, msg = await EastBlueService(self.bot.db).travel(interaction.user.id, island)
        await interaction.response.send_message(('✅ ' if ok else '❌ ') + msg, ephemeral=True)

    @app_commands.command(name='checkpoints', description='Show islands you have discovered.')
    async def checkpoints(self, interaction: discord.Interaction):
        points = await EastBlueService(self.bot.db).checkpoints(interaction.user.id)
        text = '\n'.join(f'• {p.replace("_"," ").title()}' for p in points) or 'No checkpoints discovered yet.'
        await interaction.response.send_message(f'🧭 **Discovered Checkpoints**\n{text}', ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(EastBlueCog(bot))
