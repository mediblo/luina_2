import discord, asyncio
from discord.ext import commands
from discord import app_commands

from utils.embed_builder import build_simple_embed
from config.settings import LOSTARK_API
from utils.http_client import get_json, get_response

class LostarkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.headers = {
            'accept' : 'application/json',
            'authorization' : f'bearer {LOSTARK_API}'
        }
        self.notices = None
        self.events = None
        
    async def cog_load(self):
        api_url = f'https://developer-lostark.game.onstove.com/news/notices'
        self.notices = await get_response(api_url, headers = self.headers)
        status = self.notices.status_code

        if 200 <= status < 300:
            print(f"🟢 LostArk_notice | Status: {status} (정상 연결)")
        
        # 🟡 노랑 동그라미: 호출 제한 초과 (429) 또는 일시적 서버 에러 (500대)
        elif status == 429 or status >= 500:
            print(f"🟡 LostArk_notice | Status: {status} (호출 제한 또는 서버 지연)")
        
        # 🔴 빨강 동그라미: 인증 실패 (401, 403) 및 기타 잘못된 요청 (400대)
        else:
            print(f"🔴 LostArk_notice | Status: {status} (인증 실패 또는 잘못된 요청)")

    @app_commands.command(name="새소식", description="로스트아크 최신 공지, 점검, 상점, 이벤트 정보를 요약하여 확인합니다.") # 공지 260624
    async def 새소식(self, interaction: discord.Interaction):
        categories = {
            "공지": {"lists": [], "max": 5, "emoji": "📢"},
            "점검": {"lists": [], "max": 3, "emoji": "🛠️"}, # '점검' 타입을 '작업' 카테고리로 분류
            "상점": {"lists": [], "max": 2, "emoji": "🛒"},
            "이벤트": {"lists": [], "max": 5, "emoji": "🎁"}
        }

        await interaction.response.defer()
        # 3. 데이터 순회하며 조건에 맞게 필터링 (최근 데이터부터 채우기)
        for item in self.notices.json():
            itype = item.get("Type")
            if itype in categories:
                # 해당 카테고리가 아직 최대 개수보다 적게 차있다면 추가
                if len(categories[itype]["lists"]) < categories[itype]["max"]:
                    date_str = item["Date"].split('T')[0] # '2026-06-24' 형태로 자르기
                    formatted_text = f"• [{item['Title']}]({item['Link']}) `({date_str})`"
                    categories[itype]["lists"].append(formatted_text)

        # 4. 임베드 구성하기
        embed = discord.Embed(
            title="✨ 로스트아크 최신 주요 소식 요약",
            color=0x3498db, # 깔끔한 파란색
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="출처 : LostArk API", icon_url=interaction.user.display_avatar.url)

        # 각 카테고리 돌면서 데이터가 있는 것만 임베드 필드(add_field)로 추가
        # '점검'의 표기 명칭만 '작업(점검)'으로 변경하여 출력
        for key, value in categories.items():
            if value["lists"]:
                field_name = f"{value['emoji']} {key if key != '점검' else '작업 (점검)'}"
                field_value = "\n".join(value["lists"])
                
                # inline=False를 주어 카테고리들이 위아래로 깔끔하게 떨어지게 만듭니다.
                embed.add_field(name=field_name, value=field_value, inline=False)

        # 5. 결과 전송
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LostarkCog(bot))