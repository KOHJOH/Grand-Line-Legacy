from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.achievement_service import AchievementService


class AchievementsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='achievements', description='View your achievements.')
    async def achievements(self, interaction: discord.Interaction):
        svc = AchievementService(self.bot.db)
        await svc.check(interaction.user.id)
        rows = await svc.list_for(interaction.user.id)
        unlocked = sum(1 for _, ok in rows if ok)
        embed = discord.Embed(title='🏆 Achievements', description=f'{unlocked}/{len(rows)} unlocked')
        lines=[]
        for ach, ok in rows[:15]:
            icon='✅' if ok else '⬜'
            lines.append(f"{icon} **{ach['name']}** — {ach['description']}")
        embed.add_field(name='Progress', value='\n'.join(lines) or 'No achievements configured.', inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='claimcheck', description='Check and claim newly completed achievements.')
    async def claimcheck(self, interaction: discord.Interaction):
        new = await AchievementService(self.bot.db).check(interaction.user.id)
        if not new:
            return await interaction.response.send_message('No new achievements ready yet.')
        msg='\n'.join([f"🏆 **{a['name']}** +{a.get('xp',0)} XP +{a.get('beli',0)} Beli" for a in new])
        await interaction.response.send_message(msg)

async def setup(bot):
    await bot.add_cog(AchievementsCog(bot))
