from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.crafting_service import CraftingService


class CraftingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="recipes", description="View available crafting recipes.")
    async def recipes(self, interaction: discord.Interaction):
        service = CraftingService(self.bot.db)
        recipes = service.all_recipes()
        embed = discord.Embed(title="🛠️ Crafting Recipes", color=discord.Color.dark_gold())
        for recipe in recipes[:12]:
            ingredients = ", ".join(f"{k} x{v}" for k, v in recipe.get("ingredients", {}).items())
            result = recipe.get("result", {})
            embed.add_field(
                name=f"{recipe['id']} — {recipe.get('name', recipe['id'])}",
                value=f"Needs: {ingredients or 'None'}\nGives: {result.get('item_id', '?')} x{result.get('quantity', 1)}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="craft", description="Craft an item by recipe ID.")
    async def craft(self, interaction: discord.Interaction, recipe_id: str):
        ok, message = await CraftingService(self.bot.db).craft(interaction.user.id, recipe_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CraftingCog(bot))
