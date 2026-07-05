from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.inventory_service import InventoryService
from services.item_service import ItemService
from services.player_service import PlayerService


class InventoryCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="inventory", description="View your inventory.")
    async def inventory(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        rows = await InventoryService(self.bot.db).list_inventory(interaction.user.id)
        if not rows:
            await interaction.response.send_message("🎒 Your inventory is empty.", ephemeral=True)
            return
        item_service = ItemService(self.bot.game_data)
        lines = []
        for r in rows[:25]:
            item = item_service.get(r["item_id"])
            name = item_service.display_name(r["item_id"])
            rarity = item_service.rarity_emoji(item.get("rarity", "common")) if item else "⚪"
            lock = " 🔒" if r["locked"] else ""
            lines.append(f"{rarity} **{name}** `x{r['quantity']}`{lock}\n`{r['item_id']}`")
        embed = discord.Embed(title="🎒 Inventory", description="\n".join(lines), color=discord.Color.gold())
        embed.set_footer(text=f"Showing {min(len(rows), 25)} of {len(rows)} item stacks")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="inspect", description="Inspect an item definition or an item in your inventory.")
    @app_commands.describe(item_id="The item id, like wooden_sword or bread")
    async def inspect(self, interaction: discord.Interaction, item_id: str):
        item_service = ItemService(self.bot.game_data)
        item = item_service.get(item_id)
        if not item:
            await interaction.response.send_message("I couldn't find that item id.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"{item_service.rarity_emoji(item.get('rarity', 'common'))} {item['name']}",
            description=item.get("description", "No description."),
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Type", value=item.get("type", "unknown"), inline=True)
        embed.add_field(name="Rarity", value=item.get("rarity", "common").title(), inline=True)
        embed.add_field(name="Sell Value", value=str(item.get("sell_value", 0)), inline=True)
        if item.get("stats"):
            embed.add_field(name="Stats", value="\n".join(f"+{v} {k}" for k, v in item["stats"].items()), inline=False)
        if item.get("effects"):
            embed.add_field(name="Use Effect", value="\n".join(f"+{v} {k}" for k, v in item["effects"].items()), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="use", description="Use a consumable item.")
    @app_commands.describe(item_id="The consumable item id")
    async def use(self, interaction: discord.Interaction, item_id: str):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        item_service = ItemService(self.bot.game_data)
        item = item_service.get(item_id)
        if not item:
            await interaction.response.send_message("Unknown item.", ephemeral=True)
            return
        if item.get("type") != "consumable":
            await interaction.response.send_message("That item cannot be used like a consumable.", ephemeral=True)
            return
        ok, msg = await InventoryService(self.bot.db).use_consumable(interaction.user.id, item_id, item.get("effects", {}))
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="drop", description="Drop an unlocked item from your inventory.")
    @app_commands.describe(item_id="The item id", quantity="How many to drop")
    async def drop(self, interaction: discord.Interaction, item_id: str, quantity: int = 1):
        if quantity <= 0:
            await interaction.response.send_message("Quantity must be positive.", ephemeral=True)
            return
        ok = await InventoryService(self.bot.db).remove_item(interaction.user.id, item_id, quantity)
        await interaction.response.send_message("🗑️ Dropped." if ok else "❌ You don't have enough, or that item is locked.", ephemeral=True)

    @app_commands.command(name="lockitem", description="Lock or unlock an item so it can't be dropped or consumed.")
    @app_commands.describe(item_id="The item id", locked="True locks it; false unlocks it")
    async def lockitem(self, interaction: discord.Interaction, item_id: str, locked: bool):
        ok = await InventoryService(self.bot.db).lock_item(interaction.user.id, item_id, locked)
        await interaction.response.send_message("🔒 Updated." if ok else "❌ Item not found.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(InventoryCog(bot))
