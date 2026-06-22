import discord, asyncio
from discord.ext import commands
from discord import app_commands

from utils.http_client import get_json
from utils.embed_builder import build_simple_embed

from config.settings import riot_api

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_load(self):
        self.riot_emoji = await self.bot.fetch_application_emojis()
        
async def setup(bot):
    await bot.add_cog(HelpCog(bot))