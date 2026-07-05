from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.npc_service import NPCService


class NPCCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name='localnpcs', description='List NPCs on your current island.')
    async def localnpcs(self, interaction: discord.Interaction):
        island, npcs = await NPCService(self.bot.db).list_for_player(interaction.user.id)
        embed = discord.Embed(title=f'👥 NPCs — {island}', color=discord.Color.green())
        if not npcs:
            embed.description = 'No NPCs are active here yet.'
        for npc in npcs[:12]:
            embed.add_field(name=f"{npc['name']} (`{npc['id']}`)", value=f"{npc.get('role','Civilian')} • {npc.get('hint','')}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='talkto', description='Talk to a local NPC by ID.')
    async def talkto(self, interaction: discord.Interaction, npc_id: str):
        ok, line, npc = await NPCService(self.bot.db).talk(interaction.user.id, npc_id)
        if not ok:
            await interaction.response.send_message('❌ ' + line, ephemeral=True)
            return
        embed = discord.Embed(title=f"💬 {npc['name']}", description=line, color=discord.Color.blurple())
        embed.add_field(name='Role', value=npc.get('role','Civilian'))
        if npc.get('quest_hint'):
            embed.add_field(name='Quest Hint', value=npc['quest_hint'], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(NPCCog(bot))
