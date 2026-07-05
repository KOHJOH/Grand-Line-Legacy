from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.equipment_service import EquipmentService
from services.inventory_service import InventoryService
from services.item_service import ItemService
from services.player_service import PlayerService


class EquipmentCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="equipment", description="View your equipped gear.")
    async def equipment(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        item_service = ItemService(self.bot.game_data)
        service = EquipmentService(self.bot.db)
        equipment = await service.get_equipment(interaction.user.id)
        labels = [
            ("Weapon", equipment["weapon_item_id"]),
            ("Armor", equipment["armor_item_id"]),
            ("Accessory 1", equipment["accessory_1_item_id"]),
            ("Accessory 2", equipment["accessory_2_item_id"]),
            ("Tool", equipment["tool_item_id"]),
            ("Cosmetic", equipment["cosmetic_item_id"]),
        ]
        lines = [f"**{label}:** {item_service.display_name(item_id) if item_id else 'None'}" for label, item_id in labels]
        stats = await service.total_stats(interaction.user.id, item_service.get)
        if stats:
            lines.append("\n**Total Gear Stats**")
            lines.extend(f"+{v} {k}" for k, v in stats.items())
        embed = discord.Embed(title="🧥 Equipment", description="\n".join(lines), color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="equip", description="Equip a weapon, armor, accessory, tool, or cosmetic.")
    @app_commands.describe(item_id="The item id", accessory_slot="For accessories only: 1 or 2")
    async def equip(self, interaction: discord.Interaction, item_id: str, accessory_slot: int = 1):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        item_service = ItemService(self.bot.game_data)
        item = item_service.get(item_id)
        if not item:
            await interaction.response.send_message("Unknown item.", ephemeral=True)
            return
        if not item_service.can_equip(item_id):
            await interaction.response.send_message("That item cannot be equipped.", ephemeral=True)
            return
        owned = await InventoryService(self.bot.db).get_item(interaction.user.id, item_id)
        if not owned:
            await interaction.response.send_message("You don't own that item.", ephemeral=True)
            return
        preferred = "accessory_2_item_id" if accessory_slot == 2 else "accessory_1_item_id"
        slot_column = item_service.equipment_slot_for(item_id, preferred)
        if not slot_column:
            await interaction.response.send_message("That item has no valid equipment slot.", ephemeral=True)
            return
        await EquipmentService(self.bot.db).equip(interaction.user.id, item_id, slot_column)
        await interaction.response.send_message(f"✅ Equipped **{item['name']}**.", ephemeral=True)

    @app_commands.command(name="unequip", description="Unequip a gear slot.")
    @app_commands.describe(slot="weapon, armor, accessory1, accessory2, tool, or cosmetic")
    async def unequip(self, interaction: discord.Interaction, slot: str):
        ok = await EquipmentService(self.bot.db).unequip(interaction.user.id, slot)
        await interaction.response.send_message("✅ Unequipped." if ok else "❌ Unknown slot.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(EquipmentCog(bot))
