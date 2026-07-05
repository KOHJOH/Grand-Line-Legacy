from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.item_service import ItemService
from services.loot_service import LootService
from services.player_service import PlayerService


class LootCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _format_rewards(self, rewards: dict, item_service: ItemService) -> str:
        lines = [f"💰 Beli: **{rewards.get('beli', 0)}**", f"✨ XP: **{rewards.get('xp', 0)}**"]
        items = rewards.get("items", [])
        if items:
            lines.append("\n🎁 Items")
            for item in items:
                lines.append(f"• {item_service.display_name(item['item_id'])} x{item.get('quantity', 1)}")
        else:
            lines.append("\nNo item drops this time.")
        return "\n".join(lines)

    @app_commands.command(name="lootchest", description="Open a test treasure chest from the loot table.")
    @app_commands.describe(chest_id="starter_chest or resource_crate")
    async def lootchest(self, interaction: discord.Interaction, chest_id: str = "starter_chest"):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        rewards = await LootService(self.bot.db, self.bot.game_data).roll_chest(interaction.user.id, chest_id)
        item_service = ItemService(self.bot.game_data)
        embed = discord.Embed(title="📦 Treasure Opened", description=self._format_rewards(rewards, item_service), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="grantbossloot", description="Dev/testing: roll a boss loot table manually.")
    @app_commands.describe(boss_id="Boss id like higuma, buggy, axe_hand_morgan")
    async def grantbossloot(self, interaction: discord.Interaction, boss_id: str):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        rewards = await LootService(self.bot.db, self.bot.game_data).roll_boss(interaction.user.id, boss_id)
        item_service = ItemService(self.bot.game_data)
        embed = discord.Embed(title=f"👑 Boss Loot: {boss_id}", description=self._format_rewards(rewards, item_service), color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LootCog(bot))
