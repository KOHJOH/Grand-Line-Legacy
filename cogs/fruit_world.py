from __future__ import annotations

import os
import discord
from discord import app_commands
from discord.ext import commands

from services.fruit_world_service import FruitWorldService


class FruitWorldCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name='fruitspawns', description='View active Devil Fruit spawns.')
    async def fruitspawns(self, interaction: discord.Interaction):
        rows = await FruitWorldService(self.bot.db).active_spawns()
        embed = discord.Embed(title='🍈 Active Fruit Rumors', color=discord.Color.purple())
        if not rows:
            embed.description = 'No active fruit rumors right now.'
        for row in rows:
            embed.add_field(name=f"{row['fruit_name']} • {row['rarity']}", value=f"Island: {row['island']}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='searchfruit', description='Search your current island for a Devil Fruit spawn.')
    async def searchfruit(self, interaction: discord.Interaction):
        ok, msg = await FruitWorldService(self.bot.db).find(interaction.user.id)
        await interaction.response.send_message(('✅ ' if ok else '❌ ') + msg, ephemeral=True)

    @app_commands.command(name='spawnfruit', description='Owner: spawn a random Devil Fruit rumor.')
    async def spawnfruit(self, interaction: discord.Interaction, island: str | None = None):
        owner = os.getenv('OWNER_ID')
        if owner and str(interaction.user.id) != owner:
            await interaction.response.send_message('Owner only.', ephemeral=True)
            return
        ok, msg = await FruitWorldService(self.bot.db).spawn_random(island)
        await interaction.response.send_message(('✅ ' if ok else '❌ ') + msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FruitWorldCog(bot))
