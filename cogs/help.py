import discord
from discord.ext import commands
from discord import app_commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test", description="퐁!") # 샤갈~
    async def test(self, interaction: discord.Interaction):
        emojis = await self.bot.fetch_application_emojis()

        await interaction.response.send_message(f"{discord.utils.get(emojis, name="Senna")} {discord.utils.get(emojis, name="Zoe")} {discord.utils.get(emojis, name="Aatrox")}")

async def setup(bot):
    await bot.add_cog(HelpCog(bot))