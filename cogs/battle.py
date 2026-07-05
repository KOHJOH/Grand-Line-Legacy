from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.battle_service import BattleService
from services.player_service import PlayerService


class BattleCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="battle", description="Start a random NPC battle on your current island.")
    @app_commands.describe(enemy_id="Optional enemy id for testing, like bandit_recruit")
    async def battle(self, interaction: discord.Interaction, enemy_id: str | None = None):
        if not await PlayerService(self.bot.db).get_player(interaction.user.id):
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        ok, message, enemy = await BattleService(self.bot.db, self.bot.game_data).start(interaction.user.id, enemy_id)
        if not ok:
            await interaction.response.send_message("❌ " + message, ephemeral=True)
            return
        embed = discord.Embed(title="⚔️ Battle Started", description=message, color=discord.Color.red())
        if enemy:
            embed.add_field(name="Enemy HP", value=f"{enemy['hp']}/{enemy['hp']}", inline=True)
            embed.add_field(name="Enemy Attack", value=str(enemy.get("attack", 0)), inline=True)
        embed.set_footer(text="Use /battleaction action:attack, heavy, defend, or flee.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="battleaction", description="Take your turn in battle.")
    @app_commands.describe(action="attack, heavy, defend, or flee")
    async def battleaction(self, interaction: discord.Interaction, action: str):
        ok, message, ended = await BattleService(self.bot.db, self.bot.game_data).action(interaction.user.id, action)
        color = discord.Color.dark_red() if not ended else discord.Color.gold()
        embed = discord.Embed(title="⚔️ Battle", description=message, color=color)
        await interaction.response.send_message(embed=embed, ephemeral=True)



async def setup(bot: commands.Bot):
    await bot.add_cog(BattleCog(bot))
