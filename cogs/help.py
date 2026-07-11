import discord
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
                    "usage": "/계산기 식:2+4*4",
                    "desc": "사칙연산 식을 계산합니다."
                },
                "시간": {
                    "usage": "/시간 [공개여부:공개/비공개]",
                    "desc": "현재 UTC 및 한국 시간을 확인합니다."
                },
                "가위바위보": {
                    "usage": "/가위바위보 플레이어:가위 [공개여부:공개/비공개]",
                    "desc": "루이나와 가위바위보를 합니다."
                },
                "소라고동": {
                    "usage": "/소라고동 질문:오늘 점심 뭐먹지? [공개여부:공개/비공개]",
                    "desc": "소라고동이 예/아니오를 알려줍니다."
                },
                "선택": {
                    "usage": "/선택 주제1:A 주제2:B [주제3:C] ... [공개여부:공개/비공개]",
                    "desc": "입력한 항목 중 하나를 선택합니다."
                },
                "b64": {
                    "usage": "/b64 모드:인코딩 문장:Hello",
                    "desc": "Base64 인코딩/디코딩을 수행합니다."
                },
                "청소": {
                    "usage": "/청소 갯수:10",
                    "desc": "최근 메시지를 삭제합니다."
                },
                "초대": {
                    "usage": "/초대",
                    "desc": "봇의 초대 링크를 출력합니다."
                },
                "날씨": {
                    "usage": "/날씨 지역:서울 [공개여부:공개/비공개]",
                    "desc": "한국 지역의 현재 날씨를 조회합니다."
                },
                "환율": {
                    "usage": "/환율 [국가:KRW] [금액:1000] [공개여부:공개/비공개]",
                    "desc": "실시간 환율 정보를 조회합니다."
                },
                "사전": {
                    "usage": "/사전 단어:인공지능 [공개여부:공개/비공개]",
                    "desc": "국립국어원 사전 정보를 조회합니다."
                },
                "가사": {
                    "usage": "/가사 노래:Butter [가수:BTS] [공개여부:공개/비공개]",
                    "desc": "노래 가사를 검색합니다."
                },
                "전적": {
                    "usage": "/전적 닉네임:Hide on bush#KR1 [모드:개인/2인 랭크] [공개여부:공개/비공개]",
                    "desc": "최근 10게임 전적을 조회합니다."
                },
                "롤": {
                    "usage": "/롤 닉네임:Hide on bush#KR1 [공개여부:공개/비공개]",
                    "desc": "소환사 정보를 조회합니다."
                },
                "롤챔프": {
                    "usage": "/롤챔프 챔피언:아리 [공개여부:공개/비공개]",
                    "desc": "챔피언 스킬 정보를 조회합니다."
                },
                "스킬가속": {
                    "usage": "/스킬가속 챔피언:아리 스킬가속:50 [상대챔피언:제이스] [상대스킬가속:30] [공개여부:공개/비공개]",
                    "desc": "스킬 가속 적용 후 쿨타임을 계산합니다."
                },
                "로아_공지": {
                    "usage": "/로아_공지",
                    "desc": "로스트아크 최신 공지, 점검, 상점, 이벤트 정보를 요약하여 확인합니다."
                },
                "로아_이벤트": {
                    "usage": "/로아_이벤트",
                    "desc": "로스트아크 이벤트 정보를 요약하여 확인합니다."
                },
                "로아_캐릭터": {
                    "usage": "/로아_캐릭터 닉네임:메루미나 [공개여부:공개/비공개]",
                    "desc": "로스트아크 캐릭터 정보를 요약하여 확인합니다."
                },
                "메이플_등록": {
                    "usage": "/메이플_등록 닉네임:타락파워전사",
                    "desc": "해당 닉네임을 등록합니다."
                },
                "메이플_삭제": {
                    "usage": "/메이플_삭제 닉네임:타락파워전사",
                    "desc": "해당 닉네임을 삭제합니다."
                },
                "메이플_랭킹": {
                    "usage": "/메이플_랭킹",
                    "desc": "등록된 닉네임들의 랭킹을 조회합니다."
                },
                "메이플_캐릭터": {
                    "usage": "/메이플_캐릭터 닉네임:타락파워전사 [공개여부:공개/비공개]",
                    "desc": "메이플스토리 캐릭터 정보를 조회합니다."
                },
                "메이플_공지": {
                    "usage": "/메이플_공지",
                    "desc": "메이플스토리 최신 공지를 조회합니다."
                },
                "메이플_이벤트": {
                    "usage": "/메이플_이벤트",
                    "desc": "메이플스토리 최신 이벤트를 조회합니다."
                }
            }
    
    async def cog_load(self):
        self.riot_emoji = await self.bot.fetch_application_emojis()
        
    @app_commands.command(name="도움말", description="명령어 도움말을 확인합니다.")
    @app_commands.describe(명령어="명령어 이름 (선택)")
    async def help_command(self, interaction: discord.Interaction, 명령어: Optional[str] = None):
        if 명령어 is None:
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
                value=("`/날씨 /환율 /사전 /가사`"), inline=False)

            embed.add_field(
                name="🎮 League of Legends",
                value=("`/롤 /전적 /롤챔프 /스킬가속`"), inline=False)

            embed.add_field(
                name="🎮 Lost Ark",
                value=("`/로아_공지 /로아_이벤트 /로아_캐릭터`"), inline=False)
            
            embed.add_field(
                    name="🎮 MapleStory",
                    value=("`/메이플_등록 /메이플_삭제 /메이플_랭킹`\n"
                        "`/메이플_캐릭터 /메이플_공지 /메이플_이벤트`"), inline=False)

            embed.add_field(
                name="🔍 상세 도움말",
                value="`/도움말 명령어이름`\n예시: `/도움말 롤`")

        else:
            data = self.HELP_DATA.get(명령어)

            if not data:
                await interaction.response.send_message(
                    "해당 명령어를 찾을 수 없습니다.",
                    ephemeral=True
                )
                return

            embed = build_simple_embed(
                title=f"📖 {명령어}",
                description=data["desc"]
            )

            embed.add_field(
                name="사용법",
                value=f"`{data['usage']}`",
                inline=False
            )

        embed.set_author(name=f"구동 시간 : {self.bot.start_time}")
        embed.url = "https://www.notion.so/Luina-39580ffbfd3580bbb2a3e85c97027b40?source=copy_link"
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))