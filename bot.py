from __future__ import annotations

import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.database import Database
from core.data_loader import GameData

COGS = [
    "cogs.start",
    "cogs.profile",
    "cogs.inventory",
    "cogs.equipment",
    "cogs.loot",
    "cogs.combat",
    "cogs.fruits",
    "cogs.haki",
    "cogs.islands",
    "cogs.world",
    "cogs.news_events",
    "cogs.ships",
    "cogs.stats",
    "cogs.quests",
    "cogs.battle",
    "cogs.progression",
    "cogs.crew",
    "cogs.achievements",
    "cogs.professions",
    "cogs.bounty",
    "cogs.market",
    "cogs.crafting",
    "cogs.fishing",
    "cogs.dungeons",
    "cogs.world_progression",
    "cogs.ship_jobs",
    "cogs.alpha_admin",
    "cogs.raids",
    # East Blue is exposed through the prefix router to avoid Discord's 100 global slash-command cap.
    "cogs.milestone_b",
    "cogs.prefix",
]


class GrandLineBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        # Prefix commands need Message Content Intent enabled in the Discord Developer Portal.
        intents.message_content = True
        super().__init__(command_prefix="-", intents=intents)
        self.db: Database | None = None
        self.game_data: GameData | None = None

    async def setup_hook(self) -> None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is missing. Add it to Railway variables.")

        self.db = Database(database_url)
        await self.db.connect()
        await self.db.initialize_schema("sql/schema.sql")
        logging.info("Database schema initialized")

        self.game_data = GameData.load_from_folder("data")

        for cog in COGS:
            try:
                await self.load_extension(cog)
                logging.info("Loaded extension %s", cog)
            except Exception:
                logging.exception("Failed to load extension %s", cog)
                # Keep the bot online during alpha even if one feature cog has an integration issue.
                # The error remains visible in Railway logs so we can patch it without taking the whole bot down.
                continue

        guild_id = os.getenv("SYNC_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logging.info("Synced commands to guild %s", guild_id)
        else:
            await self.tree.sync()
            logging.info("Synced global commands")

    async def close(self) -> None:
        if self.db:
            await self.db.close()
        await super().close()


async def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing. Add it to Railway variables.")
    bot = GrandLineBot()
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
