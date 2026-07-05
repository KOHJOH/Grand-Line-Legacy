from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.player_service import PlayerService

class WorldCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="map", description="View known islands.")
    async def map(self, interaction: discord.Interaction):
        islands = self.bot.game_data.islands
        lines = [f"• **{i['name']}** — {i['region']} Lv.{i['level_range']}" for i in islands[:20]]
        await interaction.response.send_message(embed=discord.Embed(title="🗺️ World Map", description="\n".join(lines)), ephemeral=True)

    @app_commands.command(name="questboard", description="View quests on your current island.")
    async def questboard(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        quests = [q for q in self.bot.game_data.quests if q.get("island_id") == player["current_island"]]
        if not quests:
            await interaction.response.send_message("No quests here yet.", ephemeral=True)
            return
        lines = [f"• `{q['id']}` — **{q['name']}**: {q['objective']}" for q in quests[:20]]
        await interaction.response.send_message(embed=discord.Embed(title="📜 Quest Board", description="\n".join(lines)), ephemeral=True)

    @app_commands.command(name="bosses", description="View bosses near your current island.")
    async def bosses(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        bosses = [b for b in self.bot.game_data.bosses if b.get("island_id") == player["current_island"]]
        if not bosses:
            await interaction.response.send_message("No known bosses here.", ephemeral=True)
            return
        lines = [f"• `{b['id']}` — **{b['name']}** Lv.{b['level']} ({b['type']})" for b in bosses[:20]]
        await interaction.response.send_message(embed=discord.Embed(title="👑 Boss Board", description="\n".join(lines)), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(WorldCog(bot))
