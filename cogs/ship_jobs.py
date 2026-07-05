from __future__ import annotations

import random
import discord
from discord import app_commands
from discord.ext import commands

from services.wallet_service import WalletService


class ShipJobsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="shipmission", description="Run a quick ship mission for Beli, XP, and ship progression.")
    async def shipmission(self, interaction: discord.Interaction):
        player = await self.bot.db.fetchrow("SELECT level, stamina FROM players WHERE discord_id=$1", interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        if int(player["stamina"]) < 15:
            await interaction.response.send_message("❌ You need at least 15 stamina. Use `/recover`.", ephemeral=True)
            return
        missions = ["Escort a merchant ship", "Evade a Marine patrol", "Salvage a wreck", "Map a rough current", "Rescue a stranded sailor"]
        mission = random.choice(missions)
        xp = 25 + int(player["level"]) * 5
        beli = random.randint(120, 350) + int(player["level"]) * 20
        await self.bot.db.execute("UPDATE players SET stamina=stamina-15, xp=xp+$2 WHERE discord_id=$1", interaction.user.id, xp)
        await WalletService(self.bot.db).add(interaction.user.id, beli, "shipmission")
        await self.bot.db.execute(
            "INSERT INTO ship_mission_log(discord_id, mission_name, xp_gained, beli_gained) VALUES($1,$2,$3,$4)",
            interaction.user.id,
            mission,
            xp,
            beli,
        )
        embed = discord.Embed(title="⛵ Ship Mission Complete", color=discord.Color.teal())
        embed.description = f"**{mission}**\n+{xp} XP\n+{beli:,} Beli\n-15 Stamina"
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ShipJobsCog(bot))
