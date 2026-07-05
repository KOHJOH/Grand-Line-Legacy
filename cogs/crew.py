from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.crew_service import CrewService


class CrewCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="crew", description="View your crew.")
    async def crew(self, interaction: discord.Interaction):
        svc = CrewService(self.bot.db)
        crew, members = await svc.roster(interaction.user.id)
        if not crew:
            return await interaction.response.send_message("You are not in a crew yet. Use /crewcreate.", ephemeral=True)
        embed = discord.Embed(title=f"🏴‍☠️ {crew['name']}", description=f"Captain: <@{crew['captain_id']}>")
        embed.add_field(name="Level", value=str(crew["level"]))
        embed.add_field(name="XP", value=str(crew["xp"]))
        embed.add_field(name="Treasury", value=f"{crew['treasury']:,} Beli")
        embed.add_field(name="Fame", value=str(crew["fame"]))
        roster = "\n".join([f"{m['role']} — <@{m['discord_id']}> Lv.{m['level'] or 1}" for m in members]) or "No members."
        embed.add_field(name="Roster", value=roster[:1024], inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="crewcreate", description="Create a pirate crew.")
    async def crewcreate(self, interaction: discord.Interaction, name: str):
        svc = CrewService(self.bot.db)
        crew, error = await svc.create_crew(interaction.user.id, name)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        await interaction.response.send_message(f"🏴‍☠️ Crew created: **{crew['name']}**. You are the Captain.")

    @app_commands.command(name="crewrecruit", description="Recruit a player by Discord user ID after they used /start.")
    async def crewrecruit(self, interaction: discord.Interaction, discord_id: str):
        try:
            target_id = int(discord_id.strip().replace("<@", "").replace(">", "").replace("!", ""))
        except ValueError:
            return await interaction.response.send_message("Send a valid Discord user ID or mention.", ephemeral=True)
        msg = await CrewService(self.bot.db).add_member_by_id(interaction.user.id, target_id)
        await interaction.response.send_message(msg)

    @app_commands.command(name="crewdonate", description="Donate Beli to your crew treasury.")
    async def crewdonate(self, interaction: discord.Interaction, amount: int):
        msg = await CrewService(self.bot.db).donate(interaction.user.id, amount)
        await interaction.response.send_message(msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(CrewCog(bot))
