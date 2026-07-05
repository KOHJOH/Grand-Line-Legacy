from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.island_service import IslandService
from services.item_service import ItemService
from services.player_service import PlayerService


class IslandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def service(self) -> IslandService:
        return IslandService(self.bot.db, self.bot.game_data)

    @app_commands.command(name="island", description="View your current island details.")
    async def island(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        svc = self.service()
        island = svc.get_current_island(player)
        if not island:
            await interaction.response.send_message("Your current island data is missing.", ephemeral=True)
            return
        npcs = svc.npcs_on_island(island["id"])
        shops = svc.shops_on_island(island["id"])
        treasures = svc.treasures_on_island(island["id"])
        bosses = [b for b in self.bot.game_data.bosses if b.get("island_id") == island["id"]]
        details = next((d for d in getattr(self.bot.game_data, "island_details", []) if d["island_id"] == island["id"]), {})
        embed = discord.Embed(
            title=f"🏝️ {island['name']}",
            description=island.get("description", "No description."),
            color=discord.Color.green(),
        )
        embed.add_field(name="Region", value=island.get("region", "Unknown"), inline=True)
        embed.add_field(name="Recommended", value=f"Lv.{island.get('level_range', '?')}", inline=True)
        embed.add_field(name="NPCs / Shops / Bosses", value=f"{len(npcs)} / {len(shops)} / {len(bosses)}", inline=True)
        embed.add_field(name="Districts", value=", ".join(details.get("districts", [])[:8]) or "Unknown", inline=False)
        embed.add_field(name="Secrets", value=str(len(details.get("secrets", []))), inline=True)
        embed.add_field(name="Treasures", value=str(len(treasures)), inline=True)
        embed.add_field(name="Connections", value=", ".join(island.get("travel_connections", [])) or "None", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="travelmenu", description="Show islands you can sail to from your current island.")
    async def travelmenu(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        svc = self.service()
        dests = svc.available_destinations(player["current_island"])
        if not dests:
            await interaction.response.send_message("No direct routes from here yet.", ephemeral=True)
            return
        lines = [f"• `{d['id']}` — **{d['name']}** Lv.{d.get('level_range','?')}" for d in dests]
        await interaction.response.send_message(embed=discord.Embed(title="⛵ Travel Routes", description="\n".join(lines)), ephemeral=True)

    @app_commands.command(name="travel", description="Travel to a connected island.")
    @app_commands.describe(destination_id="Use /travelmenu to see valid destination ids")
    async def travel(self, interaction: discord.Interaction, destination_id: str):
        ok, msg = await self.service().travel(interaction.user.id, destination_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="npcs", description="List named NPCs on your current island.")
    async def npcs(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        npcs = self.service().npcs_on_island(player["current_island"])
        if not npcs:
            await interaction.response.send_message("No named NPCs here yet.", ephemeral=True)
            return
        lines = [f"• `{n['id']}` — **{n['name']}** ({n.get('role','NPC')})" for n in npcs[:25]]
        await interaction.response.send_message(embed=discord.Embed(title="👥 Local NPCs", description="\n".join(lines)), ephemeral=True)

    @app_commands.command(name="talknpc", description="Talk to a named NPC on your island.")
    @app_commands.describe(npc_id="NPC id from /npcs")
    async def talknpc(self, interaction: discord.Interaction, npc_id: str):
        ok, line, meta = await self.service().talk_to_npc(interaction.user.id, npc_id)
        if not ok:
            await interaction.response.send_message("❌ " + line, ephemeral=True)
            return
        npc = self.service().npc(npc_id)
        embed = discord.Embed(title=f"💬 {npc['name']}", description=f"> {line}", color=discord.Color.blurple())
        if meta:
            embed.set_footer(text=f"Friendship: {meta['friendship']} | Talks: {meta['talks']}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="shops", description="List shops on your current island.")
    async def shops(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        shops = self.service().shops_on_island(player["current_island"])
        if not shops:
            await interaction.response.send_message("No shops here yet.", ephemeral=True)
            return
        lines = [f"• `{s['id']}` — **{s['name']}** ({len(s.get('inventory', []))} items)" for s in shops]
        await interaction.response.send_message(embed=discord.Embed(title="🏪 Local Shops", description="\n".join(lines)), ephemeral=True)

    @app_commands.command(name="shop", description="View a shop's inventory.")
    @app_commands.describe(shop_id="Shop id from /shops")
    async def shop(self, interaction: discord.Interaction, shop_id: str):
        shop = self.service().shop(shop_id)
        if not shop:
            await interaction.response.send_message("Unknown shop.", ephemeral=True)
            return
        item_service = ItemService(self.bot.game_data)
        lines = []
        for listing in shop.get("inventory", []):
            item_id = listing["item_id"]
            lines.append(f"• `{item_id}` — **{item_service.display_name(item_id)}** — {listing['price']} Beli")
        await interaction.response.send_message(embed=discord.Embed(title=f"🏪 {shop['name']}", description="\n".join(lines)), ephemeral=True)

    @app_commands.command(name="buy", description="Buy an item from a local shop.")
    @app_commands.describe(shop_id="Shop id", item_id="Item id", quantity="Quantity to buy")
    async def buy(self, interaction: discord.Interaction, shop_id: str, item_id: str, quantity: int = 1):
        ok, msg = await self.service().buy_item(interaction.user.id, shop_id, item_id, quantity)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="searchtreasure", description="Search your current island for an unclaimed treasure.")
    async def searchtreasure(self, interaction: discord.Interaction):
        ok, msg = await self.service().search_treasure(interaction.user.id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="gather", description="Gather a local resource from your current island.")
    @app_commands.describe(resource_id="Optional resource id. Leave empty for random local resource.")
    async def gather(self, interaction: discord.Interaction, resource_id: str | None = None):
        ok, msg = await self.service().gather_resource(interaction.user.id, resource_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(IslandsCog(bot))
