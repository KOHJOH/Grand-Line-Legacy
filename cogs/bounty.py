from __future__ import annotations

import os
import discord
from discord import app_commands
from discord.ext import commands

from services.bounty_service import BountyService

class BountyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='bounty', description='View your bounty poster.')
    async def bounty(self, interaction: discord.Interaction):
        p = await BountyService(self.bot.db).profile(interaction.user.id)
        if not p:
            return await interaction.response.send_message('Use /start first.', ephemeral=True)
        embed = discord.Embed(title='📜 WANTED', description=f"**{p['username']}**")
        embed.add_field(name='Bounty', value=f"{p['bounty'] or 0:,} Beli")
        embed.add_field(name='Faction', value=p['faction'] or 'Unaffiliated')
        embed.add_field(name='Title', value=p['title'] or 'Rookie')
        embed.set_footer(text='DEAD OR ALIVE')
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='bountyleaderboard', description='Top wanted players.')
    async def bountyleaderboard(self, interaction: discord.Interaction):
        rows = await BountyService(self.bot.db).leaderboard()
        lines = [f"#{i+1} <@{r['discord_id']}> — {r['bounty'] or 0:,} Beli (Lv.{r['level']})" for i, r in enumerate(rows)]
        await interaction.response.send_message('📜 **Most Wanted**\n' + ('\n'.join(lines) or 'No bounties yet.'))

    @app_commands.command(name='addbounty', description='Owner-only: add bounty to a player.')
    async def addbounty(self, interaction: discord.Interaction, discord_id: str, amount: int, reason: str):
        owner_id = os.getenv('OWNER_ID')
        if owner_id and str(interaction.user.id) != str(owner_id):
            return await interaction.response.send_message('Owner only.', ephemeral=True)
        target = int(discord_id.strip().replace('<@','').replace('>','').replace('!',''))
        msg = await BountyService(self.bot.db).add_bounty(target, amount, reason)
        await interaction.response.send_message(msg)

async def setup(bot):
    await bot.add_cog(BountyCog(bot))
