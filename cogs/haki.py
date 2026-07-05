from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.haki_service import HakiService
from services.player_service import PlayerService


class HakiCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def service(self) -> HakiService:
        return HakiService(self.bot.db, self.bot.game_data)

    @app_commands.command(name="haki", description="View your Haki progression.")
    async def haki(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        service = self.service()
        await service.unlock_available(interaction.user.id)
        profile = await service.get_profile(interaction.user.id)
        embed = discord.Embed(title="⚫ Haki", description="Your current Haki progression.", color=discord.Color.dark_purple())
        for haki_type in ("observation", "armament", "conqueror"):
            meta = service.get_haki_meta(haki_type)
            unlocked = profile[f"{haki_type}_unlocked"]
            level = int(profile[f"{haki_type}_level"])
            xp = int(profile[f"{haki_type}_xp"])
            active = profile[f"active_{haki_type}"]
            status = "Unlocked" if unlocked else f"Locked until level {meta['unlock_level']}"
            if haki_type == "conqueror" and not profile["conqueror_potential"]:
                status = "Dormant potential not awakened"
            embed.add_field(
                name=f"{meta['emoji']} {meta['name']}",
                value=f"{status}\nTier: **{service.tier_for(haki_type, level)}**\nLevel: **{level}/100** ({xp}/100 XP)\nActive: **{'Yes' if active else 'No'}**",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="trainhaki", description="Train Observation, Armament, or Conqueror's Haki.")
    @app_commands.describe(haki_type="observation, armament, or conqueror")
    async def trainhaki(self, interaction: discord.Interaction, haki_type: str):
        result = await self.service().train(interaction.user.id, haki_type)
        await interaction.response.send_message(("✅ " if result.ok else "❌ ") + result.message, ephemeral=True)

    @app_commands.command(name="observe", description="Toggle Observation Haki for combat bonuses.")
    async def observe(self, interaction: discord.Interaction):
        result = await self.service().activate(interaction.user.id, "observation")
        await interaction.response.send_message(("👁️ " if result.ok else "❌ ") + result.message, ephemeral=True)

    @app_commands.command(name="coat", description="Toggle Armament Haki coating.")
    async def coat(self, interaction: discord.Interaction):
        result = await self.service().activate(interaction.user.id, "armament")
        await interaction.response.send_message(("⚫ " if result.ok else "❌ ") + result.message, ephemeral=True)

    @app_commands.command(name="conquer", description="Toggle Conqueror's Haki pressure if awakened.")
    async def conquer(self, interaction: discord.Interaction):
        result = await self.service().activate(interaction.user.id, "conqueror")
        await interaction.response.send_message(("👑 " if result.ok else "❌ ") + result.message, ephemeral=True)

    @app_commands.command(name="hakistats", description="View exact combat bonuses from active Haki.")
    async def hakistats(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        mods = await self.service().combat_modifiers(interaction.user.id)
        embed = discord.Embed(title="📊 Haki Combat Bonuses", color=discord.Color.dark_purple())
        embed.add_field(name="Dodge Bonus", value=f"{mods['dodge_bonus'] * 100:.1f}%", inline=True)
        embed.add_field(name="Crit Bonus", value=f"{mods['crit_bonus'] * 100:.1f}%", inline=True)
        embed.add_field(name="Damage Bonus", value=f"{mods['damage_bonus'] * 100:.1f}%", inline=True)
        embed.add_field(name="Defense Bonus", value=f"{mods['defense_bonus'] * 100:.1f}%", inline=True)
        embed.add_field(name="Conqueror Pressure", value=f"{mods['pressure_bonus'] * 100:.1f}%", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HakiCog(bot))
