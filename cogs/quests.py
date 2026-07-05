from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.player_service import PlayerService
from services.quest_service import QuestService


class QuestsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="questboard", description="View quests available in your current area.")
    async def questboard(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        current_island = player["current_island"]
        quests = [q for q in self.bot.game_data.quests if current_island in q.get("islands", []) or "Any" in q.get("islands", [])]
        if not quests:
            await interaction.response.send_message("No quests are posted here yet.", ephemeral=True)
            return
        lines = []
        for q in quests[:10]:
            obj = q.get("objective", {})
            lines.append(f"📜 **{q['name']}** `/{q['id']}`\n{q.get('description', 'No description.')}\nObjective: `{obj.get('type', 'task')}` **{obj.get('amount', 1)}x {obj.get('target', '')}**")
        embed = discord.Embed(title=f"Quest Board — {current_island}", description="\n\n".join(lines), color=discord.Color.green())
        embed.set_footer(text="Use /queststart quest_id:<id> to accept one.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="quests", description="View your active quests.")
    async def quests(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        service = QuestService(self.bot.db, self.bot.game_data)
        rows = await service.active_quests(interaction.user.id)
        if not rows:
            await interaction.response.send_message("You have no active quests. Try `/questboard`.", ephemeral=True)
            return
        lines = []
        for row in rows:
            q = service.get_definition(row["quest_id"]) or {"name": row["quest_id"], "objective": {}}
            progress = dict(row["progress"] or {})
            objective = q.get("objective", {})
            lines.append(f"📜 **{q['name']}** `{row['quest_id']}`\n{self._progress_text(objective, progress)}")
        embed = discord.Embed(title="Active Quests", description="\n\n".join(lines), color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="queststart", description="Accept a quest by id.")
    @app_commands.describe(quest_id="Example: foosha_training")
    async def queststart(self, interaction: discord.Interaction, quest_id: str):
        if not await PlayerService(self.bot.db).get_player(interaction.user.id):
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        ok, message = await QuestService(self.bot.db, self.bot.game_data).start_quest(interaction.user.id, quest_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + message, ephemeral=True)

    @app_commands.command(name="questturnin", description="Turn in a completed quest.")
    @app_commands.describe(quest_id="The quest id")
    async def questturnin(self, interaction: discord.Interaction, quest_id: str):
        ok, message, rewards = await QuestService(self.bot.db, self.bot.game_data).turn_in(interaction.user.id, quest_id)
        if not ok:
            await interaction.response.send_message("❌ " + message, ephemeral=True)
            return
        reward_text = []
        if rewards:
            if rewards.get("xp"):
                reward_text.append(f"+{rewards['xp']} XP")
            if rewards.get("beli"):
                reward_text.append(f"+{rewards['beli']} Beli")
            for item_id, qty in (rewards.get("items") or {}).items():
                reward_text.append(f"+{qty} {item_id}")
            if rewards.get("leveled"):
                reward_text.append(f"Level up! Now level {rewards['level']}")
        await interaction.response.send_message(f"✅ {message}\n" + (" • ".join(reward_text) or "No rewards."), ephemeral=True)

    @app_commands.command(name="questabandon", description="Abandon an active quest.")
    @app_commands.describe(quest_id="The quest id")
    async def questabandon(self, interaction: discord.Interaction, quest_id: str):
        ok = await QuestService(self.bot.db, self.bot.game_data).abandon_quest(interaction.user.id, quest_id)
        await interaction.response.send_message("🗑️ Quest abandoned." if ok else "❌ That quest is not active.", ephemeral=True)

    def _progress_text(self, objective: dict, progress: dict) -> str:
        kind = objective.get("type", "task")
        amount = int(objective.get("amount", 1))
        target = objective.get("target", "objective")
        if kind == "kill":
            return f"Defeat `{target}`: **{int(progress.get('kills', 0))}/{amount}**"
        if kind == "collect":
            return f"Collect `{target}`: **{int(progress.get('collected', 0))}/{amount}**"
        if kind == "talk":
            return "Talk objective: **Done**" if progress.get("talked") else "Talk objective: **Not done**"
        if kind == "explore":
            return "Explore objective: **Done**" if progress.get("explored") else "Explore objective: **Not done**"
        return "Progress tracked."


async def setup(bot: commands.Bot):
    await bot.add_cog(QuestsCog(bot))
