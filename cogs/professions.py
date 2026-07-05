from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.profession_service import ProfessionService, PROFESSIONS


class ProfessionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='professions', description='View gathering and crafting profession levels.')
    async def professions(self, interaction: discord.Interaction):
        rows = await ProfessionService(self.bot.db).list_professions(interaction.user.id)
        embed = discord.Embed(title='🧰 Professions')
        for r in rows:
            label = PROFESSIONS[r['profession']]['label']
            embed.add_field(name=label, value=f"Level {r['level']} | XP {r['xp']} | Actions {r['total_actions']}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='gatherjob', description='Work a profession: fishing, mining, foraging, cooking.')
    async def gatherjob(self, interaction: discord.Interaction, profession: str):
        result, err = await ProfessionService(self.bot.db).gather(interaction.user.id, profession.lower())
        if err:
            return await interaction.response.send_message(err, ephemeral=True)
        await interaction.response.send_message(
            f"🧰 **{result['profession']}** complete: +{result['xp']} profession XP, +{result['beli']} Beli, "
            f"found **{result['qty']}x {result['resource']}**. Profession level: {result['level']}."
        )

async def setup(bot):
    await bot.add_cog(ProfessionsCog(bot))
