from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.player_service import PlayerService
from services.haki_service import HakiService


def _safe(record, key: str, default="Unknown"):
    """Safely read asyncpg.Record fields even if the database is missing older columns."""
    if record is None:
        return default
    data = dict(record)
    value = data.get(key, default)
    return default if value is None else value


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="profile", description="View your character profile.")
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        service = PlayerService(self.bot.db)
        player = await service.get_player(interaction.user.id)

        if not player:
            await interaction.followup.send("Use `/start` first.", ephemeral=True)
            return

        username = _safe(player, "username", interaction.user.display_name)

        embed = discord.Embed(
            title=f"🏴‍☠️ {username}",
            description="Your Grand Line: Legacy character profile.",
            color=discord.Color.dark_gold(),
        )

        level = _safe(player, "level", 1)
        xp = _safe(player, "xp", 0)
        beli = _safe(player, "beli", 0)
        race = _safe(player, "race", "Human")
        faction = _safe(player, "faction", "Independent")
        current_island = _safe(player, "current_island", "Foosha Village")
        bounty = _safe(player, "bounty", 0)
        title = _safe(player, "title", "Rookie")
        crew_name = _safe(player, "crew_name", "None")
        devil_fruit = _safe(player, "devil_fruit", "None")

        hp = _safe(player, "hp", 100)
        max_hp = _safe(player, "max_hp", 100)
        stamina = _safe(player, "stamina", 100)
        max_stamina = _safe(player, "max_stamina", 100)

        embed.add_field(name="Level", value=str(level))
        embed.add_field(name="XP", value=str(xp))
        embed.add_field(name="Beli", value=f"{beli}")
        embed.add_field(name="Race", value=str(race))
        embed.add_field(name="Faction", value=str(faction))
        embed.add_field(name="Island", value=str(current_island))
        embed.add_field(name="Title", value=str(title))
        embed.add_field(name="Bounty", value=f"{bounty}")
        embed.add_field(name="Crew", value=str(crew_name))
        embed.add_field(name="Devil Fruit", value=str(devil_fruit))
        embed.add_field(name="HP", value=f"{hp}/{max_hp}")
        embed.add_field(name="Stamina", value=f"{stamina}/{max_stamina}")

        try:
            haki = await HakiService(self.bot.db, self.bot.game_data).get_profile(interaction.user.id)
            observation = haki.get("observation_level", 0) if isinstance(haki, dict) else haki["observation_level"]
            armament = haki.get("armament_level", 0) if isinstance(haki, dict) else haki["armament_level"]
            conqueror = haki.get("conqueror_level", 0) if isinstance(haki, dict) else haki["conqueror_level"]
            haki_text = (
                f"👁️ Observation {observation}/100\n"
                f"⚫ Armament {armament}/100\n"
                f"👑 Conqueror {conqueror}/100"
            )
        except Exception:
            haki_text = "👁️ Observation 0/100\n⚫ Armament 0/100\n👑 Conqueror 0/100"

        embed.add_field(name="Haki", value=haki_text, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))
