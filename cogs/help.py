import discord, asyncio
from discord.ext import commands
from discord import app_commands
from typing  import Optional

from utils.embed_builder import build_simple_embed

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.HELP_DATA = {
            "정보": {
                "usage": "/정보",
                "desc": "루이나 봇 정보를 확인합니다."
            },
            "핑": {
                "usage": "/핑",
                "desc": "현재 봇의 응답 속도를 확인합니다."
            },
            "계산기": {
                "usage": "/계산기 msg:2+4*4",
                "desc": "사칙연산 식을 계산합니다."
            },
            "시간": {
                "usage": "/시간",
                "desc": "현재 UTC 및 한국 시간을 확인합니다."
            },
            "가위바위보": {
                "usage": "/가위바위보 player:가위",
                "desc": "루이나와 가위바위보를 합니다."
            },
            "소라고동": {
                "usage": "/소라고동 msg:오늘 점심 뭐먹지?",
                "desc": "소라고동이 예/아니오를 알려줍니다."
            },
            "선택": {
                "usage": "/선택 A B C",
                "desc": "입력한 항목 중 하나를 선택합니다."
            },
            "b64": {
                "usage": "/b64 mode:인코딩 msg:Hello",
                "desc": "Base64 인코딩/디코딩을 수행합니다."
            },
            "청소": {
                "usage": "/청소 count:10",
                "desc": "최근 메시지를 삭제합니다."
            },
            "날씨": {
                "usage": "/날씨 city:서울",
                "desc": "한국 지역의 현재 날씨를 조회합니다."
            },
            "환율": {
                "usage": "/환율 country:USD price:100",
                "desc": "실시간 환율 정보를 조회합니다."
            },
            "사전": {
                "usage": "/사전 word:인공지능",
                "desc": "국립국어원 사전 정보를 조회합니다."
            },
            "가사": {
                "usage": "/가사 song:Butter artist:BTS",
                "desc": "노래 가사를 검색합니다."
            },
            "전적": {
                "usage": "/전적 nickname:Hide on bush#KR1",
                "desc": "최근 10게임 전적을 조회합니다."
            },
            "롤": {
                "usage": "/롤 nickname:Hide on bush#KR1",
                "desc": "소환사 정보를 조회합니다."
            },
            "롤챔프": {
                "usage": "/롤챔프 champion:아리",
                "desc": "챔피언 스킬 정보를 조회합니다."
            },
            "스킬가속": {
                "usage": "/스킬가속 champion:아리 cooldown_reduction:50",
                "desc": "스킬 가속 적용 후 쿨타임을 계산합니다."
            }
        }
    
    async def cog_load(self):
        self.riot_emoji = await self.bot.fetch_application_emojis()
        
    @app_commands.command(name="도움말", description="명령어 도움말을 확인합니다.")
    @app_commands.describe(command="명령어 이름 (선택)")
    async def help_command(self, interaction: discord.Interaction, command: Optional[str] = None):
        if command is None:
            embed = build_simple_embed(
                title="📚 루이나 도움말",
                description="사용 가능한 명령어 목록"
            )

            embed.add_field(
                name="💡 일반",
                value=("`/정보 /핑 /계산기 /시간 /가위바위보`\n"
                    "`/소라고동 /선택 /b64 /청소`"), inline=False)

            embed.add_field(
                name="🌐 API",
                value=("`/날씨 /환율 /사전 /가사`"))

            embed.add_field(
                name="🎮 League of Legends",
                value=("`/롤 /전적 /롤챔프 /스킬가속`"))

            embed.add_field(
                name="🔍 상세 도움말",
                value="`/도움말 명령어이름`\n예시: `/도움말 롤`")

        else:
            data = self.HELP_DATA.get(command)

            if not data:
                await interaction.response.send_message(
                    "해당 명령어를 찾을 수 없습니다.",
                    ephemeral=True
                )
                return

            embed = build_simple_embed(
                title=f"📖 {command}",
                description=data["desc"]
            )

            embed.add_field(
                name="사용법",
                value=f"`{data['usage']}`",
                inline=False
            )

        embed.set_author(name=f"구동 시간 : {self.bot.start_time}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))