from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.fruit_service import FruitService
from services.player_service import PlayerService


class FruitsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def fruit_service(self) -> FruitService:
        return FruitService(self.bot.db, self.bot.game_data)

    @app_commands.command(name="fruitdex", description="View the Devil Fruit encyclopedia.")
    async def fruitdex(self, interaction: discord.Interaction):
        service = self.fruit_service()
        entries = await service.list_fruitdex(interaction.user.id, 25)
        seen = {e["fruit_id"]: e for e in entries}
        lines: list[str] = []
        for fruit in self.bot.game_data.fruits[:25]:
            entry = seen.get(fruit["id"])
            status = "❔ Unseen"
            if entry:
                status = "👁️ Seen"
                if entry["owned"]:
                    status = "🍈 Owned"
                if entry["mastered"]:
                    status = "⭐ Mastered"
                if entry["awakened"]:
                    status = "🌟 Awakened"
            awaken = "✅ Awakens" if fruit.get("awakenable") else "—"
            lines.append(f"{service.rarity_emoji(fruit['rarity'])} **{fruit['name']}** `{fruit['id']}`\n{status} • {fruit['category']} • {awaken}")
        embed = discord.Embed(title="🍈 FruitDex", description="\n\n".join(lines), color=discord.Color.green())
        embed.set_footer(text=f"Showing 25 of {len(self.bot.game_data.fruits)} fruit records")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="fruitfind", description="Search your current island for a Devil Fruit. Alpha test command.")
    async def fruitfind(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        ok, msg, fruit = await self.fruit_service().find_fruit(interaction.user.id, player["current_island"])
        if not ok or not fruit:
            await interaction.response.send_message("❌ " + msg, ephemeral=True)
            return
        embed = discord.Embed(title="🍈 Devil Fruit Found", description=msg, color=discord.Color.green())
        embed.add_field(name="Fruit ID", value=f"`{fruit['id']}`", inline=True)
        embed.add_field(name="Rarity", value=fruit["rarity"].title(), inline=True)
        embed.add_field(name="Inventory Item", value=f"`fruit_{fruit['id']}`", inline=False)
        embed.set_footer(text="Use /eatfruit fruit_id:<id> to eat it.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="eatfruit", description="Eat a Devil Fruit item from your inventory.")
    @app_commands.describe(fruit_id="Fruit id, like mera_mera or goro_goro")
    async def eatfruit(self, interaction: discord.Interaction, fruit_id: str):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        ok, msg = await self.fruit_service().eat_fruit(interaction.user.id, fruit_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="fruit", description="View your current Devil Fruit.")
    async def fruit(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        service = self.fruit_service()
        current = await service.get_player_fruit(interaction.user.id)
        if not current:
            await interaction.response.send_message("🍈 You do not have a Devil Fruit yet.", ephemeral=True)
            return
        fruit = service.get(current["fruit_id"])
        embed = discord.Embed(title=f"🍈 {fruit['name']}", description=fruit.get("description", ""), color=discord.Color.green())
        embed.add_field(name="Category", value=fruit["category"].title(), inline=True)
        embed.add_field(name="Rarity", value=f"{service.rarity_emoji(fruit['rarity'])} {fruit['rarity'].title()}", inline=True)
        embed.add_field(name="Mastery", value=f"{current['mastery']}/100 ({current['mastery_xp']}/100 XP)", inline=True)
        embed.add_field(name="Awakened", value="Yes" if current["awakened"] else "No", inline=True)
        ability_lines = []
        for a in fruit.get("abilities", []):
            lock = "✅" if current["mastery"] >= a.get("mastery_required", 0) else "🔒"
            ability_lines.append(f"{lock} `{a['id']}` — **{a['name']}** \nMastery {a['mastery_required']} • {a['stamina_cost']} stamina • {a['cooldown_seconds']}s CD")
        embed.add_field(name="Abilities", value="\n".join(ability_lines[:6]) or "None", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="fruittrain", description="Train your Devil Fruit mastery.")
    async def fruittrain(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        ok, msg = await self.fruit_service().train(interaction.user.id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="fruitability", description="Use one of your Devil Fruit abilities outside boss combat.")
    @app_commands.describe(ability_id="Ability id shown by /fruit")
    async def fruitability(self, interaction: discord.Interaction, ability_id: str):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        ok, msg, _ability = await self.fruit_service().use_ability(interaction.user.id, ability_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="awakenfruit", description="Attempt to awaken your Devil Fruit after Mastery 100.")
    async def awakenfruit(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        ok, msg = await self.fruit_service().awaken(interaction.user.id)
        await interaction.response.send_message(("🌟 " if ok else "❌ ") + msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FruitsCog(bot))
