import logging

import discord
from discord.ext import commands

from shedbot.config.config import settings

logging.basicConfig()
log = logging.getLogger("shedbot.main")
log.setLevel(logging.DEBUG)

VERSION = "0.3.0"

intents = discord.Intents.default()
intents.members = True  # must also be enabled in Dev Portal

bot = commands.Bot(command_prefix="/", intents=intents)
initial_extensions = ["cogs.schedule"]


def main():
    log.info("Starting ShedBot")
    log.info(f"Using {settings.dynaconf_namespace} config")

    for extension in initial_extensions:
        bot.load_extension(extension)

    bot.run(settings.bot_token)


@bot.event
async def on_ready():
    print("Bot is ready")

if __name__ == "__main__":
    main()
