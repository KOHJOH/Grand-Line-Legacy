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
]

class GrandLineBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = False
        super().__init__(command_prefix="!", intents=intents)
        self.db: Database | None = None
        self.game_data: GameData | None = None

    async def setup_hook(self) -> None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is missing. Add it to .env")

        self.db = Database(database_url)
        await self.db.connect()
        self.game_data = GameData.load_from_folder("data")

        for cog in COGS:
            await self.load_extension(cog)

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
        raise RuntimeError("DISCORD_TOKEN is missing. Add it to .env")
    bot = GrandLineBot()
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
