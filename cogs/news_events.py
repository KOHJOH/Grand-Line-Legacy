from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.event_service import EventService
from services.news_service import NewsService
from services.player_service import PlayerService


class NewsEventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def event_service(self) -> EventService:
        return EventService(self.bot.db, self.bot.game_data.world_events)

    @app_commands.command(name="news", description="Read the latest World News articles.")
    async def news(self, interaction: discord.Interaction, limit: app_commands.Range[int, 1, 10] = 5):
        articles = await NewsService(self.bot.db).latest(limit)
        if not articles:
            await interaction.response.send_message("📰 No World News articles yet.", ephemeral=True)
            return
        lines = []
        for article in articles:
            lines.append(f"`#{article['id']}` **{article['headline']}**\n{article['body'][:160]}")
        embed = discord.Embed(title="📰 World News", description="\n\n".join(lines))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="article", description="Read a specific World News article.")
    async def article(self, interaction: discord.Interaction, article_id: int):
        article = await NewsService(self.bot.db).get_article(article_id)
        if not article:
            await interaction.response.send_message("Article not found.", ephemeral=True)
            return
        embed = discord.Embed(title=f"📰 {article['headline']}", description=article["body"])
        embed.add_field(name="Category", value=article["category"])
        if article["island_id"]:
            embed.add_field(name="Location", value=article["island_id"])
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="events", description="View active world events.")
    async def events(self, interaction: discord.Interaction):
        player = await PlayerService(self.bot.db).get_player(interaction.user.id)
        island_id = player["current_island"] if player else None
        events = await self.event_service().active_events(island_id)
        if not events:
            await interaction.response.send_message("🌍 No active events near you right now.", ephemeral=True)
            return
        lines = []
        for event in events[:10]:
            lines.append(
                f"• **{event['name']}** (`{event['event_type']}`)\n"
                f"  {event['description']}\n"
                f"  Ends: <t:{int(event['ends_at'].timestamp())}:R>"
            )
        await interaction.response.send_message(
            embed=discord.Embed(title="🌍 Active World Events", description="\n\n".join(lines)),
            ephemeral=True,
        )

    @app_commands.command(name="eventtemplates", description="View possible world events. Useful for admins and testing.")
    async def eventtemplates(self, interaction: discord.Interaction):
        templates = self.event_service().list_event_templates()
        lines = [f"• `{e['id']}` — **{e['name']}** ({e.get('region', 'Global')})" for e in templates[:25]]
        await interaction.response.send_message(
            embed=discord.Embed(title="📅 Event Templates", description="\n".join(lines)),
            ephemeral=True,
        )

    @app_commands.command(name="startevent", description="Admin/test: start a world event by ID.")
    @app_commands.checks.has_permissions(administrator=True)
    async def startevent(self, interaction: discord.Interaction, event_id: str):
        try:
            event = await self.event_service().start_event(event_id, started_by=interaction.user.id)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            f"🌍 Started **{event['name']}**. Ends <t:{int(event['ends_at'].timestamp())}:R>.",
            ephemeral=True,
        )

    @app_commands.command(name="endevent", description="Admin/test: end an active world event by active event ID.")
    @app_commands.checks.has_permissions(administrator=True)
    async def endevent(self, interaction: discord.Interaction, active_event_id: int):
        row = await self.event_service().end_event(active_event_id)
        if not row:
            await interaction.response.send_message("No active event found with that ID.", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Ended **{row['name']}**.", ephemeral=True)

    @startevent.error
    @endevent.error
    async def admin_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message("You need Administrator permission for that command.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(NewsEventsCog(bot))
