import discord, asyncio
from discord.ext import commands
import os # 파일
from datetime import datetime, timezone, timedelta # 시간
import base64
import re

from utils.logger import logger
from config.settings import BOT_TOKEN # 설정값
from services.log_service import flush_task

intents = discord.Intents.all() # 모든 권한

class Luina(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, description="Test Luina") # 명령어 접두사 설정, 권한 설정
        KST = timezone(timedelta(hours=9))
        self.start_time = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]

    async def on_ready(self):
        logger.info(f"로그인 완료: {self.user} ({self.start_time})", "Discord")
        asyncio.create_task(flush_task)

    async def on_message(self, message):
        if message.author.bot: # bot은 제외
            return

        if message.channel.id == 1307325562569621525 and (m := re.match(r"^<a?:[\w]+:([\d]+)>$", message.content)): # 이모지 확대
            if message.content.startswith("<a:"):
                ext = "gif"
            else:
                ext = "png"
                
            embed = discord.Embed(color=message.author.color)
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar)
            embed.set_image(url=f"https://cdn.discordapp.com/emojis/{m.group(1)}.{ext}")
            
            await message.channel.send(embed=embed)
            await message.delete()
            return
        
        elif message.channel.id == 1268563900891402240: # b64 decode
            try:
                # .unicode('UTF-8') 제거 후 바로 인코딩하여 바이트로 변환
                msg_bytes = message.content.encode('utf-8') 
                msg_decode = base64.b64decode(msg_bytes)
                msg_data = msg_decode.decode('utf-8') # 한글 깨짐 방지를 위해 utf-8로 디코딩 권장
                
                await message.channel.send(msg_data)
            except Exception as e:
                await message.channel.send(f"⚠️ 디코딩 실패: 올바른 Base64 형식이 아닙니다.")
            return

    async def setup_hook(self):
        @self.tree.error # 에러 로그 처리
        async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
            developer_id = 442284517223301120
            developer = self.get_user(developer_id)
            if developer:
                await developer.send(f"{interaction.user} / /{interaction.command.name if interaction.command else 'Unknown'} / {error}")

            logger.exception(msg=interaction.command.name if interaction.command else 'Unknown', user = interaction.user)
            
            # 사용자에게 에러 알림 (이미 응답했는지 여부에 따라 처리)
            if interaction.response.is_done():
                await interaction.followup.send("에러!!", ephemeral=True)
            else:
                await interaction.response.send_message("에러!!", ephemeral=True)

        for filename in os.listdir('./cogs'): # cogs 폴더의 모든 파일을 불러옴
            if filename.endswith('.py') and not filename.startswith('__'): # .py로 끝나고 __로 시작하지 않는 파일만 불러옴
                await self.load_extension(f'cogs.{filename[:-3]}') # 확장자를 제외한 파일 이름으로 cogs를 불러옴
                logger.info(f"코그 로드 완료: cogs.{filename[:-3]}", "Discord")


bot = Luina()

if __name__ == '__main__':
    # 설정 파일에서 가져온 토큰으로 봇 실행
    bot.run(BOT_TOKEN)