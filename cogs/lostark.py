import discord, asyncio
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
import json

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

        api_url = f'https://developer-lostark.game.onstove.com/news/events'
        self.events = await get_response(api_url, headers = self.headers)
        status = self.events.status_code

        if 200 <= status < 300:
            print(f"🟢 LostArk_event | Status: {status} (정상 연결)")
        
        # 🟡 노랑 동그라미: 호출 제한 초과 (429) 또는 일시적 서버 에러 (500대)
        elif status == 429 or status >= 500:
            print(f"🟡 LostArk_event | Status: {status} (호출 제한 또는 서버 지연)")
        
        # 🔴 빨강 동그라미: 인증 실패 (401, 403) 및 기타 잘못된 요청 (400대)
        else:
            print(f"🔴 LostArk_event | Status: {status} (인증 실패 또는 잘못된 요청)")

#########################################################################################################

    @app_commands.command(name="로아_공지", description="로스트아크 최신 공지, 점검, 상점, 이벤트 정보를 요약하여 확인합니다.") # 공지 260624
    async def lostark_notices(self, interaction: discord.Interaction):
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
        await interaction.followup.send(embed=embed)

#########################################################################################################

    @app_commands.command(name="로아_이벤트", description="로스트아크 이벤트 정보를 요약하여 확인합니다.") # 이벤트 231101 / 260625
    async def lostark_events(self, interaction: discord.Interaction):
        def parse_end_date(date_str):
            """ISO 8601 날짜를 datetime 객체로 변환"""
            if not date_str:
                return None
            try:
                if '.' in date_str:
                    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
                else:
                    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                return None
        
        events = self.events.json()

        KST = timezone(timedelta(hours=9))
        now = datetime.now(KST)
        seven_days_later = now + timedelta(days=7)
        
        ending_soon = []
        ongoing = []

        for event in events:
            title = event.get("Title")
            link = event.get("Link")
            end_dt = parse_end_date(event.get("EndDate"))
            
            # 종료일이 없는 경우 진행중으로 처리
            if not end_dt:
                ongoing.append(f"• [{title}]({link}) (상시)")
                continue
                
            # 이미 종료된 이벤트는 스킵
            if end_dt < now:
                continue
                
            # MM.DD 포맷으로 변환
            date_str = end_dt.strftime("%m.%d")
            
            # 텍스트 포맷: • [이벤트명](링크) (~MM.DD)
            event_text = f"• [{title}]({link}) (~{date_str})"
            
            # 일주일 이내 종료 여부 체크
            if end_dt <= seven_days_later:
                ending_soon.append(event_text)
            else:
                ongoing.append(event_text)

        # 활성화된 총 이벤트 개수 계산
        total_active_events = len(ending_soon) + len(ongoing)

        # 임베드 생성
        embed = build_simple_embed(
            title=f"✨ 로스트아크 이벤트 ({total_active_events}개)"
        )
        
        # 본문(description) 구성
        description_text = ""
        
        # 곧 종료 리스트 추가
        description_text += "**🔥 곧 종료**\n"
        if ending_soon:
            description_text += "\n".join(ending_soon) + "\n\n"
        else:
            description_text += "• 일주일 내로 종료되는 이벤트가 없습니다.\n\n"
            
        # 진행중 리스트 추가
        description_text += "**📌 진행중**\n"
        if ongoing:
            description_text += "\n".join(ongoing)
        else:
            description_text += "• 진행 중인 이벤트가 없습니다."

        # 완성된 텍스트를 임베드 설명에 삽입
        embed.description = description_text
    
        await interaction.response.send_message(embed=embed)

#########################################################################################################

    @app_commands.command(name="로아_캐릭터", description="로스트아크 캐릭터 정보를 요약하여 확인합니다.") # 캐릭터 231101 / 버튼 추가 231106 / 궁극기 삭제 241120 / 260625
    @app_commands.describe(닉네임="닉네임")
    @app_commands.describe(공개여부="공개 여부 (기본값: 공개)")
    @app_commands.choices(공개여부=[
        app_commands.Choice(name="공개", value=1),
        app_commands.Choice(name="비공개", value=0)
    ])
    async def lostark_character(self, interaction: discord.Interaction, 닉네임: str, 공개여부: int = 1):
        공개여부 = 공개여부 == 0  # 공개 여부를 boolean으로 변환
        await interaction.response.defer(ephemeral=공개여부)
        
        loawa_url = f"https://loawa.com/char/{닉네임}"
        api_url = f"https://developer-lostark.game.onstove.com/armories/characters/{닉네임}"
        api_response = await get_response(api_url, headers=self.headers)

        # 1. API 에러 및 존재하지 않는 캐릭터 처리
        if api_response.text == "null" or not api_response.text:
            await interaction.followup.send(f"❌ **{닉네임}** - 존재하지 않거나 검색할 수 없는 닉네임입니다.")
            return
        elif api_response.status_code != 200:
            await interaction.followup.send("⚠️ 로스트아크 API 서버와 통신 중 에러가 발생했습니다.")
            return
        
        api_data = api_response.json()
        profile = api_data.get("ArmoryProfile")

        if not profile:
            await interaction.followup.send("❌ 캐릭터 프로필 정보를 불러올 수 없습니다.")
            return

        # 추가 정보 추출 (클래스)
        char_class = profile.get("CharacterClassName", "알 수 없음")
        server_name = profile.get("ServerName", "N/A")
        guild_name = profile.get("GuildName", "없음")

        # 2. 임베드 기본 세팅 (색상 적용 및 Description 활용)
        # 기존 build_simple_embed 대신 discord.Embed를 직접 사용하여 디자인 자유도를 높임
        embed = discord.Embed(
            title=f"👑 {닉네임} ({char_class})",
            description=f"**서버:** {server_name} | **길드:** {guild_name}",
            color=0x2b2d31, # 디스코드 다크모드 배경과 잘 어울리는 세련된 회색 (원하는 Hex 색상으로 변경 가능)
            url=loawa_url
        )
        
        # 썸네일(우측 상단 작은 이미지) 적용
        if profile.get("CharacterImage"):
            embed.set_thumbnail(url=profile["CharacterImage"])

        # 3. 레벨 및 기본 정보 (인라인으로 가로 배치하여 깔끔하게)
        embed.add_field(name="🌟 아이템 레벨", value=f"**{profile.get('ItemAvgLevel', '0')}**", inline=True)
        embed.add_field(name="📈 레벨", value=f"전투 **{profile.get('CharacterLevel', '0')}**\n원정대 **{profile.get('ExpeditionLevel', '0')}**", inline=True)
        embed.add_field(name="🏡 영지", value=f"{profile.get('TownName', '이름 없음')}", inline=True)

        # 4. 스탯 및 특성 정보 파싱
        basic_stats = []
        combat_stats = []
        
        if api_data.get("ArmoryProfile") and "Stats" in api_data["ArmoryProfile"]:
            for stat in api_data["ArmoryProfile"]["Stats"]:
                if stat["Type"] in ["공격력", "최대 생명력"]:
                    basic_stats.append(f"**{stat['Type']}** : {stat['Value']}")
                elif stat["Type"] in ["치명", "특화", "신속", "제압", "인내", "숙련"]:
                    # 0인 특성은 굳이 보여주지 않도록 필터링 (깔끔함 유지)
                    if stat['Value'] != "0":
                        combat_stats.append(f"**{stat['Type']}** : {stat['Value']}")
                    
        embed.add_field(name="📊 기본 스탯", value="\n".join(basic_stats) if basic_stats else "정보 없음", inline=True)
        embed.add_field(name="⚔️ 전투 특성", value="\n".join(combat_stats) if combat_stats else "정보 없음", inline=True)
        
        # 빈 필드를 하나 넣어 레이아웃 정렬 (디스코드 임베드는 한 줄에 최대 3개 필드)
        embed.add_field(name="\u200b", value="\u200b", inline=True) 

        # 5. 장비 정보 파싱 (이모지 추가)
        equip_list = []
        target_equip_types = ["무기", "투구", "상의", "하의", "장갑", "어깨"]
        equip_icons = {
            "무기": "🗡️", "투구": "🪖", "상의": "👕", 
            "하의": "👖", "장갑": "🧤", "어깨": "🛡️"
        }
        
        if api_data.get("ArmoryEquipment"):
            for eq in api_data["ArmoryEquipment"]:
                if eq["Type"] in target_equip_types:
                    icon = equip_icons.get(eq["Type"], "🔸")
                    equip_list.append(f"{icon} **{eq['Type']}** : {eq['Name']}")
                    
        embed.add_field(name="🎒 주요 장비", value="\n".join(equip_list) if equip_list else "장착된 장비 없음", inline=False)

        embed.set_footer(text="LostArk Open API", icon_url=interaction.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed, ephemeral=공개여부, view=chaBtn(interaction=interaction, data=api_data, nickname=닉네임))

class chaBtn(discord.ui.View):
    def __init__(self, interaction: discord.Interaction | discord.Member, data:json, nickname:str):
        super().__init__(timeout=10)
        self.interaction = interaction
        self.data = data
        self.nickname = nickname
        self.profile = data.get("ArmoryProfile")
        self.embed = build_simple_embed(
                title=f"👑 {self.nickname} ({self.profile['CharacterClassName']})",
                description=f"**서버:** {self.profile['ServerName']} | **길드:** {self.profile['GuildName']}"
            )
        self.embed.set_footer(text="LostArk Open API", icon_url=interaction.user.display_avatar.url)
        self.embed.url=f"https://loawa.com/char/{self.nickname}"

        if self.profile.get("CharacterImage"):
            self.embed.set_thumbnail(url=self.profile["CharacterImage"])
    
    async def on_timeout(self):
        # 1. view에 속한 모든 버튼을 반복문으로 돌며 비활성화(disabled)시킵니다.
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @discord.ui.button(label="스킬", style=discord.ButtonStyle.success)
    async def skill_btn(self, interaction : discord.Interaction, btn : discord.ui.Button):
        RUNE_EMOJI = {
            "고급": "🟢",
            "희귀": "🔵",
            "영웅": "🟣",
            "전설": "🟠"
        }
        idx = 0
        if interaction.user.id == self.interaction.user.id:
            for skill in self.data['ArmorySkills']:
                if skill['Level'] == 1: continue

                tripod_text = ""

                for tripod in skill['Tripods']:
                    if not tripod['IsSelected']: continue
                    tripod_text += f"> {tripod['Slot']} {tripod['Name']}\n"

                # 룬
                rune_text = ""

                if skill.get("Rune"):
                    rune = skill["Rune"]
                    rune_text = (
                        f"{RUNE_EMOJI.get(rune['Grade'],'✨')} "
                        f"**{rune['Grade']} {rune['Name']}**\n"
                    )

                value = (
                    f"{rune_text}"
                    f"{tripod_text}"
                )

                self.embed.add_field(
                    name=f"⚔️ {skill['Name']}  (Lv.{skill['Level']})",
                    value=value
                )
                idx+=1
                if idx == 2:
                    self.embed.add_field(name='', value='')
                    idx=0

            
            await interaction.response.edit_message(embed=self.embed, view=None)
        
    @discord.ui.button(label="수집", style=discord.ButtonStyle.success)
    async def collect_btn(self, interaction : discord.Interaction, btn : discord.ui.Button):
        COLLECT_EMOJI = {
            "모코코 씨앗": "🌱",
            "섬의 마음": "🏝️",
            "위대한 미술품": "🖼️",
            "거인의 심장": "❤️",
            "이그네아의 징표": "🍃",
            "항해 모험물": "🚢",
            "세계수의 잎": "🌳",
            "오르페우스의 별": "⭐",
            "기억의 오르골": "🎵",
            "크림스네일의 해도": "🗺️",
            "누크만의 환영석": "💎",
        }

        for collectible in self.data["Collectibles"]:
            icon = COLLECT_EMOJI.get(collectible["Type"], "📌")
            self.embed.add_field(
                name=f"{icon} {collectible['Type']}",
                value=f"`{collectible['Point']} / {collectible['MaxPoint']}`",
                inline=True
            )
        await interaction.response.edit_message(embed=self.embed, view=None)

#########################################################################################################



async def setup(bot):
    await bot.add_cog(LostarkCog(bot))