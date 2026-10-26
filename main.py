import discord
from discord.ext import commands
import json
import os
import asyncio
from config import TOKEN

CONFIG_FILE = "sniper_config.json"

def get_prefix(bot, message):
    if not message.guild:
        return ",,"
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                guild_id = str(message.guild.id)
                if guild_id in data and "custom_prefix" in data[guild_id]:
                    return data[guild_id]["custom_prefix"]
        except Exception:
            pass
    return ",,"

class FlexUtilitiesBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.moderation = True
        super().__init__(command_prefix=get_prefix, intents=intents, help_command=None)

    async def setup_hook(self):
        extensions = [
            "cogs.configuration",
            "cogs.help_system",
            "cogs.tickets",
            "cogs.moderation",
            "cogs.security",
            "cogs.automod",
            "cogs.giveaways",
            "cogs.utilities"
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Loaded extension: {ext}")
            except Exception as e:
                print(f"Failed to load extension {ext}: {e}")

bot = FlexUtilitiesBot()

@bot.event
async def on_ready():
    print(f"Flex Utilities successfully logged in as {bot.user} (ID: {bot.user.id})")

async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
