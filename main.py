import asyncio, discord # 비동기함수, 디스코드
from discord.ext import commands, tasks
import os # 파일
from config.settings import BOT_TOKEN, TEST_GUILD_ID # 설정값
from cogs.general import General # 일반 명령어

intents = discord.Intents.all() # 모든 권한

class Luina(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, description="Test Luina") # 명령어 접두사 설정, 권한 설정

    async def on_ready(self):
        print(f"로그인 완료: {self.user} (id={self.user.id})")

    async def setup_hook(self):
        for filename in os.listdir('./cogs'): # cogs 폴더의 모든 파일을 불러옴
            if filename.endswith('.py') and not filename.startswith('__'): # .py로 끝나고 __로 시작하지 않는 파일만 불러옴
                await self.load_extension(f'cogs.{filename[:-3]}') # 확장자를 제외한 파일 이름으로 cogs를 불러옴
                print(f"코그 로드 완료: cogs.{filename[:-3]}")

        guild_obj = discord.Object(id=TEST_GUILD_ID)
        self.tree.copy_global_to(guild=guild_obj)
        synced = await self.tree.sync(guild=guild_obj)
        print(f"슬래시 동기화 대상 길드: {TEST_GUILD_ID}")
        print(f"동기화된 커맨드 수: {len(synced)}")
        print(f"동기화된 커맨드 목록: {[cmd.name for cmd in synced]}")
        # await self.tree.sync()
        print("슬래시 커맨드 트리가 동기화되었습니다.")

bot = Luina()

if __name__ == '__main__':
    # 설정 파일에서 가져온 토큰으로 봇 실행
    bot.run(BOT_TOKEN)