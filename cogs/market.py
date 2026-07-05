from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.market_service import MarketService


class MarketCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="market", description="Browse player market listings.")
    async def market(self, interaction: discord.Interaction):
        rows = await MarketService(self.bot.db).listings(10)
        embed = discord.Embed(title="🛒 Player Market", color=discord.Color.gold())
        if not rows:
            embed.description = "No active listings yet. Use `/marketlist` to sell an item."
        for row in rows:
            embed.add_field(
                name=f"#{row['id']} — {row['item_id']} x{row['quantity']}",
                value=f"Price: {int(row['price']):,} Beli\nSeller: <@{row['seller_id']}>",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="marketlist", description="List an item from your inventory on the market.")
    async def marketlist(self, interaction: discord.Interaction, item_id: str, quantity: int, price: int):
        ok, message = await MarketService(self.bot.db).create_listing(interaction.user.id, item_id, quantity, price)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + message, ephemeral=True)

    @app_commands.command(name="marketbuy", description="Buy a market listing by ID.")
    async def marketbuy(self, interaction: discord.Interaction, listing_id: int):
        ok, message = await MarketService(self.bot.db).buy_listing(interaction.user.id, listing_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + message, ephemeral=True)

    @app_commands.command(name="marketcancel", description="Cancel one of your market listings.")
    async def marketcancel(self, interaction: discord.Interaction, listing_id: int):
        ok, message = await MarketService(self.bot.db).cancel_listing(interaction.user.id, listing_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MarketCog(bot))
