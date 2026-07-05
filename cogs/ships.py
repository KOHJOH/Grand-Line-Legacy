from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.player_service import PlayerService
from services.ship_service import ShipService


class ShipsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def service(self) -> ShipService:
        return ShipService(self.bot.db, self.bot.game_data)

    @app_commands.command(name="shipyard", description="View ships available for purchase.")
    async def shipyard(self, interaction: discord.Interaction):
        ships = self.service().shipyard_inventory()
        if not ships:
            await interaction.response.send_message("No ships are configured yet.", ephemeral=True)
            return
        lines = []
        for ship in ships:
            price = int(ship.get("price", 0))
            price_text = "Free" if price == 0 else f"{price:,} Beli"
            lines.append(
                f"• `{ship['id']}` — **{ship['name']}** ({ship.get('class','ship')}) — {price_text}\n"
                f"  HP {ship.get('hull_hp')} | Speed {ship.get('speed')} | Cargo {ship.get('cargo_capacity')} | Cannons {ship.get('cannon_slots')}"
            )
        embed = discord.Embed(
            title="⚓ Shipyard",
            description="\n".join(lines[:10]),
            color=discord.Color.dark_blue(),
        )
        embed.set_footer(text="Use /buyship <ship_id> to purchase. Starter Raft is free once.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="buyship", description="Buy or claim a ship from the shipyard.")
    @app_commands.describe(ship_id="Ship id from /shipyard", nickname="Optional custom ship name")
    async def buyship(self, interaction: discord.Interaction, ship_id: str, nickname: str | None = None):
        ok, msg = await self.service().buy_ship(interaction.user.id, ship_id.lower(), nickname)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="ship", description="View your active ship and owned fleet.")
    async def ship(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        svc = self.service()
        active = await svc.active_ship(interaction.user.id)
        owned = await svc.owned_ships(interaction.user.id)
        if not owned:
            await interaction.response.send_message("You don't own a ship yet. Claim one with `/buyship raft`.", ephemeral=True)
            return
        embed = discord.Embed(title="🚢 Your Ships", color=discord.Color.blue())
        if active:
            definition = svc.ship_definition(active["ship_type"]) or {}
            embed.description = (
                f"**Active:** {active['nickname']} ({definition.get('name', active['ship_type'])})\n"
                f"Hull: {active['hull_hp']}/{active['max_hull_hp']} | Speed: {active['speed']} | "
                f"Cargo: {active['cargo_capacity']} | Cannons: {active['cannon_slots']} | Upgrades: {active['upgrade_level']}"
            )
        lines = []
        for ship in owned[:12]:
            marker = "⭐" if ship["active"] else "•"
            lines.append(f"{marker} ID `{ship['id']}` — **{ship['nickname']}** `{ship['ship_type']}` HP {ship['hull_hp']}/{ship['max_hull_hp']}")
        embed.add_field(name="Fleet", value="\n".join(lines), inline=False)
        embed.set_footer(text="Use /setship <id>, /repairship, /upgradeship, /sail, and /voyage.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setship", description="Set one of your owned ships as active.")
    @app_commands.describe(ship_id="Numeric ship id from /ship")
    async def setship(self, interaction: discord.Interaction, ship_id: int):
        ok, msg = await self.service().set_active_ship(interaction.user.id, ship_id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="repairship", description="Repair your active ship.")
    async def repairship(self, interaction: discord.Interaction):
        ok, msg = await self.service().repair_active_ship(interaction.user.id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="upgradeship", description="Upgrade your active ship.")
    @app_commands.describe(stat="speed, hull, or cargo")
    async def upgradeship(self, interaction: discord.Interaction, stat: str):
        ok, msg = await self.service().upgrade_active_ship(interaction.user.id, stat)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="oceanmap", description="Show known sea routes from your current island.")
    async def oceanmap(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        if not player:
            await interaction.response.send_message("Use `/start` first.", ephemeral=True)
            return
        svc = self.service()
        current = svc.islands.get(player["current_island"])
        if not current:
            await interaction.response.send_message("Your current island is missing from data.", ephemeral=True)
            return
        lines = []
        for dest_id in current.get("travel_connections", []):
            dest = svc.islands.get(dest_id)
            if dest:
                lines.append(f"• `{dest_id}` — **{dest['name']}** Lv.{dest.get('level_range','?')}")
        embed = discord.Embed(
            title=f"🌊 Ocean Routes from {current['name']}",
            description="\n".join(lines) if lines else "No sea routes known from here.",
            color=discord.Color.teal(),
        )
        embed.set_footer(text="Use /sail <destination_id> to begin a timed voyage.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="sail", description="Begin a timed ocean voyage to a connected island.")
    @app_commands.describe(destination_id="Destination id from /oceanmap")
    async def sail(self, interaction: discord.Interaction, destination_id: str):
        ok, msg = await self.service().sail(interaction.user.id, destination_id.lower())
        await interaction.response.send_message(("⛵ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="voyage", description="Check current sailing progress and discover ocean encounters.")
    async def voyage(self, interaction: discord.Interaction):
        ok, msg = await self.service().voyage_status(interaction.user.id)
        await interaction.response.send_message(("🌊 " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="resolveencounter", description="Resolve your current ocean encounter.")
    async def resolveencounter(self, interaction: discord.Interaction):
        ok, msg = await self.service().resolve_encounter(interaction.user.id)
        await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=True)

    @app_commands.command(name="oceanencounters", description="View possible ocean encounter templates.")
    async def oceanencounters(self, interaction: discord.Interaction):
        encounters = getattr(self.bot.game_data, "ocean_encounters", [])
        lines = [f"• `{e['id']}` — **{e['name']}** ({e.get('type','event')})" for e in encounters[:20]]
        await interaction.response.send_message(
            embed=discord.Embed(title="🌊 Ocean Encounter Registry", description="\n".join(lines) or "No encounters configured."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ShipsCog(bot))
