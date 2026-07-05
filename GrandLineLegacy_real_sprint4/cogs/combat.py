from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.combat_service import CombatService
from services.player_service import PlayerService


class CombatCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="bossfight", description="Start a boss fight by boss id from /bosses.")
    @app_commands.describe(boss_id="Example: higuma, buggy, axe_hand_morgan")
    async def bossfight(self, interaction: discord.Interaction, boss_id: str):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        result = await CombatService(self.bot.db, self.bot.game_data).start_boss_fight(interaction.user.id, boss_id)
        embed = discord.Embed(title=result.title, description=result.description, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="bossaction", description="Take a turn in your active boss fight.")
    @app_commands.describe(action="attack, skill, defend, focus, status, flee")
    @app_commands.choices(action=[
        app_commands.Choice(name="Attack", value="attack"),
        app_commands.Choice(name="Skill", value="skill"),
        app_commands.Choice(name="Defend", value="defend"),
        app_commands.Choice(name="Focus", value="focus"),
        app_commands.Choice(name="Status", value="status"),
        app_commands.Choice(name="Flee", value="flee"),
    ])
    async def bossaction(self, interaction: discord.Interaction, action: app_commands.Choice[str]):
        result = await CombatService(self.bot.db, self.bot.game_data).perform_action(interaction.user.id, action.value)
        color = discord.Color.green() if result.ended and "Defeated" in result.title else discord.Color.orange()
        if "💀" in result.title:
            color = discord.Color.dark_red()
        embed = discord.Embed(title=result.title, description=result.description[:3900], color=color)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="bosscodex", description="View your boss defeat records.")
    async def bosscodex(self, interaction: discord.Interaction):
        rows = await self.bot.db.fetch(
            "SELECT boss_id, defeats, first_defeated_at, last_defeated_at FROM boss_codex WHERE discord_id=$1 ORDER BY defeats DESC, boss_id LIMIT 25",
            interaction.user.id,
        )
        if not rows:
            await interaction.response.send_message("Your Boss Codex is empty. Defeat a boss first.", ephemeral=True)
            return
        boss_names = {b["id"]: b["name"] for b in self.bot.game_data.bosses}
        lines = []
        for row in rows:
            name = boss_names.get(row["boss_id"], row["boss_id"])
            lines.append(f"• **{name}** — {row['defeats']} defeat(s)")
        await interaction.response.send_message(embed=discord.Embed(title="📖 Boss Codex", description="\n".join(lines), color=discord.Color.purple()), ephemeral=True)

    @app_commands.command(name="rest", description="Recover HP and stamina outside combat.")
    async def rest(self, interaction: discord.Interaction):
        active = await CombatService(self.bot.db, self.bot.game_data).get_session(interaction.user.id)
        if active:
            await interaction.response.send_message("You can't rest during combat.", ephemeral=True)
            return
        result = await self.bot.db.execute(
            "UPDATE players SET hp=max_hp, stamina=max_stamina, updated_at=NOW() WHERE discord_id=$1",
            interaction.user.id,
        )
        if result.endswith("0"):
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        await interaction.response.send_message("🛏️ You rested and fully recovered HP/stamina.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CombatCog(bot))
