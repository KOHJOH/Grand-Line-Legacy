from __future__ import annotations

import json
import discord
from discord import app_commands
from discord.ext import commands

from services.raid_service import RaidService


class RaidsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="raidboard", description="View available raids and forming raid lobbies.")
    async def raidboard(self, interaction: discord.Interaction):
        service = RaidService(self.bot.db)
        embed = discord.Embed(title="☠️ Raid Board", color=discord.Color.dark_red())
        for raid in service.list_raids()[:5]:
            embed.add_field(
                name=f"{raid['id']} — {raid.get('name', raid['id'])}",
                value=f"Level {raid.get('level_required', 1)}+ • {raid.get('min_players', 1)}-{raid.get('max_players', 4)} players",
                inline=False,
            )
        lobbies = await service.active_lobbies()
        if lobbies:
            lobby_text = []
            for lobby in lobbies:
                party = json.loads(lobby["party"] or "[]") if isinstance(lobby["party"], str) else list(lobby["party"])
                lobby_text.append(f"#{lobby['id']} — {lobby['raid_id']} ({len(party)} joined)")
            embed.add_field(name="Forming Lobbies", value="\n".join(lobby_text), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="startraid", description="Create a raid lobby by raid ID.")
    async def startraid(self, interaction: discord.Interaction, raid_id: str):
        ok, message = await RaidService(self.bot.db).create_lobby(interaction.user.id, raid_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + message, ephemeral=True)

    @app_commands.command(name="joinraid", description="Join a raid lobby by lobby ID.")
    async def joinraid(self, interaction: discord.Interaction, lobby_id: int):
        ok, message = await RaidService(self.bot.db).join_lobby(interaction.user.id, lobby_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RaidsCog(bot))
