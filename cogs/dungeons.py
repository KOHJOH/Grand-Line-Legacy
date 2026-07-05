from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.dungeon_service import DungeonService


class DungeonsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="dungeonlist", description="View available dungeons.")
    async def dungeonlist(self, interaction: discord.Interaction):
        dungeons = DungeonService(self.bot.db).list_dungeons()
        embed = discord.Embed(title="🏯 Dungeons", color=discord.Color.red())
        for d in dungeons:
            embed.add_field(
                name=f"{d['id']} — {d.get('name', d['id'])}",
                value=f"Level {d.get('level_required', 1)}+ • {d.get('rooms', 3)} rooms • {d.get('stamina_cost', 20)} stamina",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="enterdungeon", description="Enter a dungeon by ID.")
    async def enterdungeon(self, interaction: discord.Interaction, dungeon_id: str):
        ok, message = await DungeonService(self.bot.db).enter(interaction.user.id, dungeon_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + message, ephemeral=True)

    @app_commands.command(name="dungeonaction", description="Advance through your current dungeon.")
    async def dungeonaction(self, interaction: discord.Interaction):
        ok, message = await DungeonService(self.bot.db).action(interaction.user.id)
        await interaction.response.send_message(("⚔️ " if ok else "❌ ") + message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DungeonsCog(bot))
