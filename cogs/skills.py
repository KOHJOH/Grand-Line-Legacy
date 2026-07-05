from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.skill_service import SkillService


class SkillsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name='skills', description='View learnable and known combat skills.')
    async def skills(self, interaction: discord.Interaction):
        service = SkillService(self.bot.db)
        known = {r['skill_id']: r for r in await service.known(interaction.user.id)}
        embed = discord.Embed(title='⚔️ Combat Skills', color=discord.Color.red())
        for skill in service.skills().values():
            status = 'Known' if skill['id'] in known else f"Lv {skill.get('required_level',1)} • {skill.get('cost',0)} Beli"
            mastery = f" • M{known[skill['id']]['mastery']}" if skill['id'] in known else ''
            embed.add_field(name=f"{skill['name']} (`{skill['id']}`)", value=f"{status}{mastery}\n{skill.get('description','')}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='learnskill', description='Learn a combat skill.')
    async def learnskill(self, interaction: discord.Interaction, skill_id: str):
        ok, msg = await SkillService(self.bot.db).learn(interaction.user.id, skill_id)
        await interaction.response.send_message(('✅ ' if ok else '❌ ') + msg, ephemeral=True)

    @app_commands.command(name='trainskill', description='Train a known combat skill.')
    async def trainskill(self, interaction: discord.Interaction, skill_id: str):
        ok, msg = await SkillService(self.bot.db).train(interaction.user.id, skill_id)
        await interaction.response.send_message(('✅ ' if ok else '❌ ') + msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SkillsCog(bot))
