import discord
from discord.ext import commands
import asyncio
from config import DISCORD_TOKEN
from database import Database

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

class FlexBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Initialize SQLite DB
        await Database.init_db()

        # Load Server Builder cog
        await self.load_extension("cogs.server_builder")
        
        # Sync slash commands globally
        print("Syncing slash commands...")
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("Flex is online and ready!")

bot = FlexBot()

if __name__ == "__main__":
    if DISCORD_TOKEN == "YOUR_DISCORD_BOT_TOKEN":
        print("Please configure your DISCORD_TOKEN in config.py or a .env file.")
    else:
        bot.run(DISCORD_TOKEN)
