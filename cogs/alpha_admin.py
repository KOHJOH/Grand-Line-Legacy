from __future__ import annotations

import os
import discord
from discord import app_commands
from discord.ext import commands

from services.inventory_ops import InventoryOps
from services.wallet_service import WalletService


def is_owner(user_id: int) -> bool:
    owner = os.getenv("OWNER_ID", "").strip()
    return bool(owner and str(user_id) == owner)


class AlphaAdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="grantitem", description="Owner only: grant an item to a player.")
    async def grantitem(self, interaction: discord.Interaction, user: discord.User, item_id: str, quantity: int = 1):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("Owner only.", ephemeral=True)
            return
        await InventoryOps(self.bot.db).add_item(user.id, item_id, quantity)
        await interaction.response.send_message(f"✅ Granted `{item_id}` x{quantity} to {user.mention}.", ephemeral=True)

    @app_commands.command(name="grantbeli", description="Owner only: grant Beli to a player.")
    async def grantbeli(self, interaction: discord.Interaction, user: discord.User, amount: int):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("Owner only.", ephemeral=True)
            return
        balance = await WalletService(self.bot.db).add(user.id, amount, "owner_grant")
        await interaction.response.send_message(f"✅ Granted {amount:,} Beli to {user.mention}. Balance: {balance:,}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AlphaAdminCog(bot))
