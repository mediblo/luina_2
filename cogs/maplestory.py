import discord, asyncio
from discord.ext import commands
from discord import app_commands
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from datetime import datetime, timedelta, timezone
import json

from config.settings import MAPLESTORY_API, FIREBASE_CREDENTIALS, FIREBASE_URL
from utils.http_client import get_json, get_response
from utils.embed_builder import build_simple_embed
from utils.logger import logger

class MapleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.headers= {
            'accept': 'application/json',
            'x-nxopen-api-key' : MAPLESTORY_API
        }
        self.time = datetime.now().strftime("%Y-%m-%d")
        self.notices = None
        self.events = None

        cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS))
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_URL # 본인 DB URL 입력
        })
        
    async def cog_load(self):
        notice_url = 'https://open.api.nexon.com/maplestory/v1/notice'
        self.notices = await get_response(url=notice_url, headers=self.headers)
        status = self.notices.status_code

        if 200 <= status < 300:
            logger.info(f"🟢 MapleStory_notice | Status: {status} (정상 연결)")
        
        # 🟡 노랑 동그라미: 호출 제한 초과 (429) 또는 일시적 서버 에러 (500대)
        elif status == 429 or status >= 500:
            logger.info(f"🟡 MapleStory_notice | Status: {status} (호출 제한 또는 서버 지연)")
        
        # 🔴 빨강 동그라미: 인증 실패 (401, 403) 및 기타 잘못된 요청 (400대)
        else:
            logger.info(f"🔴 MapleStory_notice | Status: {status} (인증 실패 또는 잘못된 요청)")

        event_url = 'https://open.api.nexon.com/maplestory/v1/notice-event'
        self.events = await get_response(url=event_url, headers=self.headers)
        status = self.events.status_code

        if 200 <= status < 300:
            logger.info(f"🟢 MapleStory_event | Status: {status} (정상 연결)")
        
        # 🟡 노랑 동그라미: 호출 제한 초과 (429) 또는 일시적 서버 에러 (500대)
        elif status == 429 or status >= 500:
            logger.info(f"🟡 MapleStory_event | Status: {status} (호출 제한 또는 서버 지연)")
        
        # 🔴 빨강 동그라미: 인증 실패 (401, 403) 및 기타 잘못된 요청 (400대)
        else:
            logger.info(f"🔴 MapleStory_event | Status: {status} (인증 실패 또는 잘못된 요청)")

        is_connected = db.reference('connected').get()
        if is_connected:
            logger.info("🟢 Firebase (정상연결)")
        else:
            logger.info("🔴 Firebase (연결 끊어짐)")

#########################################################################################################

    @app_commands.command(name="메이플_등록", description="해당 닉네임을 등록합니다.") # 메이플_등록 260701
    @app_commands.describe(닉네임="닉네임 (필수)")
    async def maple_add(self, interaction: discord.Interaction, 닉네임:str):
        if interaction.guild.id not in [1307325561890406452, 736512667530821653]:
            await interaction.response.send_message('개발중인 명령어 입니다.', ephemeral=True)
            return
        
        ref = db.reference(f'maple_character/{닉네임}') # 이미 있음
        if ref.get() is not None:
            await interaction.response.send_message('이미 등록된 닉네임입니다.', ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        data_url = f'https://open.api.nexon.com/maplestory/v1/id?character_name={닉네임}'
        
        api_data:dict = await get_json(url=data_url, headers=self.headers)
        
        if not api_data.get('ocid'): # 없는 이름
            await interaction.followup.send('없는 닉네임')
            return
        
        ocid = api_data['ocid']
        if user:= db.reference('maple_character').order_by_value().equal_to(ocid).get(): # 닉변한 경우 [ 기존 데이터 삭제 ]
            db.reference(f'maple_character/{list(user.keys())[0]}').delete()

        ref.set(ocid) # 추가

        developer_id = 442284517223301120
        developer = self.bot.get_user(developer_id)
        await developer.send(f"{interaction.user} 님이 {닉네임} 닉네임을 등록했습니다.\nOCID: {api_data['ocid']}")
        await interaction.followup.send('등록 완료!')

#########################################################################################################

    @app_commands.command(name="메이플_랭킹", description="등록된 닉네임들의 랭킹을 조회합니다.") # 메이플_랭킹 260701
    async def maple_ranking(self, interaction: discord.Interaction):
        if interaction.guild.id not in [1307325561890406452, 736512667530821653]:
            await interaction.response.send_message('개발중인 명령어 입니다.', ephemeral=True)
            return
        
        
        await interaction.response.defer()
        stat_url = 'https://open.api.nexon.com/maplestory/v1/character/stat?ocid='
        rank_url = f'https://open.api.nexon.com/maplestory/v1/ranking/overall?date={self.time}&ocid='

        data=[]
        for nickname, ocid in (db.reference('maple_character').get() or {}).items():
            stat_api = await get_json(url=(stat_url+ocid), headers=self.headers)
            rank_api = await get_json(url=(rank_url+ocid), headers=self.headers)
            if not rank_api['ranking'] or not stat_api['final_stat']:
                continue

            power = int(stat_api['final_stat'][-2]['stat_value'])

            data.append({
                "power": power,
                "rank_info": rank_api['ranking'][0],
            })
            await asyncio.sleep(0.3)

        # 1. 딕셔너리의 Key(랭킹 번호)를 기준으로 오름차순(1등부터) 정렬
        data.sort(key=lambda x: x["power"], reverse=True)

        # 2. 디스코드 임베드 생성
        embed = build_simple_embed(
            title="🍁 메이플스토리 캐릭터 전투력 랭킹",
            description=f"조회 기준일: `{self.time}`\n등록된 캐릭터들간의 랭킹 정보입니다."
        )

        # 3. 정렬된 데이터를 돌며 임베드에 필드 추가
        for idx, item in enumerate(data, start=1):
            # ranking 리스트 안의 첫 번째 캐릭터 정보 추출
            char_data = item['rank_info']
            
            global_rank = int(char_data["ranking"])
            format_rank = f"{global_rank:,}"

            name = char_data['character_name']
            level = char_data['character_level']
            job = char_data['class_name']
            guild = char_data['character_guildname'] or "없음"
            
            # 전투력(str -> int 변환 후 천 단위 쉼표 추가)
            power_val = item["power"]
            formatted_power = f"{power_val:,}"

            # 상위 3명에게는 특별한 이모지 부여 (시각적 효과)
            if idx == 1:
                rank_emoji = "🥇"
            elif idx == 2:
                rank_emoji = "🥈"
            elif idx == 3:
                rank_emoji = "🥉"
            else:
                rank_emoji = ""

            # 임베드에 들어갈 본문 텍스트 구성
            field_value = (
                f"**Lv.{level}** | {job}\n"
                f"길드: `{guild}`\n"
                f"전투력: **{formatted_power}**"
            )

            # 필드 추가 (Inline=False로 해서 한 줄에 하나씩 깔끔하게 떨어지게 설정)
            embed.add_field(
                name=f"{rank_emoji} {idx}위 ({format_rank}위) - {name}",
                value=field_value,
                inline=False
            )

        # 봇의 프로필 사진이 있다면 썸네일로 추가 (선택 사항)
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            
        embed.set_footer(text="Nexon Open API 제공")

        # 4. 유저에게 최종 임베드 전송
        await interaction.followup.send(embed=embed)

#########################################################################################################

    @app_commands.command(name="메이플_캐릭터", description="해당 닉네임의 정보를 조회합니다.") # 메이플_캐릭터 260701
    @app_commands.describe(닉네임="닉네임 (필수)")
    @app_commands.describe(공개여부="공개 여부를 선택합니다 (기본값 : 공개)")
    @app_commands.choices(공개여부=[
        app_commands.Choice(name="공개", value=1),
        app_commands.Choice(name="비공개", value=0)
    ])
    async def maple_character(self, interaction: discord.Interaction, 닉네임:str, 공개여부: int = 1):
        공개여부 = 공개여부 == 0  # 공개 여부를 boolean으로 변환

        await interaction.response.defer(ephemeral=공개여부)

        if (ocid:= db.reference(f'maple_character/{닉네임}').get()) is None:
            data_url = f'https://open.api.nexon.com/maplestory/v1/id?character_name={닉네임}'
            
            api_data:dict = await get_json(url=data_url, headers=self.headers)
            
            if api_data.get('ocid') is None: # 없는 이름
                await interaction.followup.send('없는 닉네임')
                return

            ocid = api_data['ocid']

        api_url = f'https://open.api.nexon.com/maplestory/v1/character/basic?ocid={ocid}'
        api_data:dict = await get_json(url=api_url, headers=self.headers)

        # 데이터 추출
        name = api_data.get("character_name", "알 수 없음")
        world = api_data.get("world_name", "알 수 없음")
        job = api_data.get("character_class", "알 수 없음")
        level = api_data.get("character_level", 0)
        exp_rate = float(api_data.get("character_exp_rate", "0.0"))
        guild = api_data.get("character_guild_name") or "없음"
        gender = api_data.get("character_gender", "-")
        image_url = api_data.get("character_image")
        
        # 해방 퀘스트 완료 여부 텍스트 변환
        is_liberated = "완료" if api_data.get("liberation_quest_clear") == "1" else "미완료"

        # 간단한 경험치 바 제작 (■: 채워짐, □: 비어있음)
        # 15.717% 면 약 1.5칸 채워짐
        filled_blocks = int(exp_rate // 5)
        empty_blocks = 20 - filled_blocks
        exp_bar = "■" * filled_blocks + "□" * empty_blocks

        # 1. 임베드 기본 설정 (제목, 설명, 색상)
        embed = build_simple_embed(
            title=f"🍁 {name} (Lv.{level})",
            description=f"**{world} 월드**의 {job} 정보입니다."
        )
        embed.url = f'https://maple.gg/u/{닉네임}'

        # 2. 캐릭터 외형 이미지 설정 (우측 대형 이미지 또는 중앙 하단)
        if image_url:
            embed.set_image(url=image_url) # 하단에 크게 노출 (코디 확인용으로 추천)
            # 만약 우측 상단에 작게 넣고 싶다면 embed.set_thumbnail(url=image_url) 사용

        # 3. 상세 정보 필드 추가 (inline=True를 주면 가로로 배치됩니다)
        embed.add_field(name="직업", value=job, inline=True)
        embed.add_field(name="성별", value=gender, inline=True)
        embed.add_field(name="길드", value=guild, inline=True)
        
        # 경험치 정보 (줄바꿈을 위해 inline=False)
        embed.add_field(
            name=f"경험치 ({exp_rate}%)", 
            value=f"`{exp_bar}`", 
            inline=False
        )
        
        embed.add_field(name="제네시스 해방", value=is_liberated, inline=True)
        
        # 생성일 처리 (ISO 포맷 문자열에서 날짜만 추출: '2026-06-18')
        create_date = api_data.get("character_date_create", "")
        if create_date:
            create_date = create_date.split("T")[0]
        embed.add_field(name="캐릭터 생성일", value=create_date, inline=True)

        # 4. 푸터(Footer) 설정
        embed.set_footer(text="DAK.GG로 이동  •  Nexon Open API 제공")

        await interaction.followup.send(embed=embed)

#########################################################################################################
    
    @app_commands.command(name="메이플_공지", description="최신 공지를 조회합니다.") # 메이플_공지 260701
    async def maple_notice(self, interaction: discord.Interaction):

        await interaction.response.defer()

        embed = build_simple_embed(
            title="🍁 메이플스토리 최근 공지사항 목록"
        )

        notice_data = self.notices.json()

        # 상위 10개만 먼저 출력 (디스코드 글자수 제한 방지 및 가독성 확보)
        # 전체를 다 띄우고 싶다면 notice_data["notice"] 로 변경 가능합니다.
        embed_description = ""
        for item in notice_data["notice"][:10]:
            title = item["title"]
            url = item["url"]
            
            # ISO 시간 포맷(2026-06-30T11:27+09:00)을 파싱하여 디스코드 타임스탬프로 변경
            # 예: <t:1782786420:d> 형태로 들어가서 디스코드 내에서 "2026년 6월 30일" 처럼 이쁘게 보입니다.
            dt = datetime.fromisoformat(item["date"])
            timestamp_str = f"<t:{int(dt.timestamp())}:d>"
            
            # 제목이 너무 길면 말줄임표(...) 처리 (디스코드 가로 폭 맞춤용)
            if len(title) > 38:
                title = title[:35] + "..."
                
            # 마크다운 링크 형식으로 한 줄씩 누적
            embed_description += f"• [{title}]({url}) — {timestamp_str}\n\n"
            
        embed.description = embed_description
        embed.set_footer(text=f"요청자: {interaction.user.display_name} | 총 {len(notice_data['notice'])}개의 공지 중 최신 10개 표시")
        
        # 썸네일에 메이플 이미지 주소를 넣으면 더 이뻐집니다 (선택사항)
        # embed.set_thumbnail(url="메이플_로고_이미지_주소")

        await interaction.followup.send(embed=embed)

#########################################################################################################
    
    @app_commands.command(name="메이플_이벤트", description="최신 이벤트를 조회합니다.") # 메이플_이벤트 260701
    async def maple_event(self, interaction: discord.Interaction):
        await interaction.response.defer()

        event_data = self.events.json()

        KST = timezone(timedelta(hours=9))
        now = datetime.now(KST)
        seven_days_later = now + timedelta(days=7)
        
        ending_soon = []
        ongoing = []

        for event in event_data["event_notice"]:
            title = event.get("title")
            url = event.get("url")
            end_date_str = event.get("date_event_end")
            
            # 1. 종료일이 없는 경우 (상시)
            if not end_date_str:
                ongoing.append(f"• [{title}]({url}) (상시)")
                continue
                
            # 2. ISO 8601 문자열(2026-07-07T23:59+09:00)을 datetime 객체로 파싱
            end_dt = datetime.fromisoformat(end_date_str)
            
            # 3. 이미 종료된 이벤트는 스킵
            if end_dt < now:
                continue
            
            # 4. 디스코드 내장 타임스탬프 생성
            # :d 는 'YYYY년 M월 D일' 형태, :R 은 'O일 후' 형태로 표시됩니다.
            end_ts_d = f"<t:{int(end_dt.timestamp())}:d>"
            end_ts_R = f"<t:{int(end_dt.timestamp())}:R>"
            
            # 5. 일주일 이내 종료 여부 체크 및 포맷팅
            if end_dt <= seven_days_later:
                # 곧 종료되는 이벤트는 며칠 남았는지(:R)를 강조합니다.
                event_text = f"• [{title}]({url}) (⏳ {end_ts_R} 종료)"
                ending_soon.append(event_text)
            else:
                # 넉넉히 남은 이벤트는 날짜(:d)로 깔끔하게 표기합니다.
                event_text = f"• [{title}]({url}) (~{end_ts_d})"
                ongoing.append(event_text)

        # 활성화된 총 이벤트 개수
        total_active_events = len(ending_soon) + len(ongoing)

        # 6. 임베드 생성 (메이플스토리 주황색)
        embed = build_simple_embed(
            title=f"✨ 메이플스토리 진행 중 이벤트 ({total_active_events}개)"
        )
        
        # 가장 최신 이벤트의 썸네일 이미지를 우측 상단에 표시 (선택사항)
        if event_data["event_notice"]:
            embed.set_thumbnail(url=event_data["event_notice"][0].get("thumbnail_url"))
        
        # 7. 본문(Description) 구성
        description_text = ""
        
        description_text += "**🔥 곧 종료 (7일 이내)**\n"
        if ending_soon:
            description_text += "\n".join(ending_soon) + "\n\n"
        else:
            description_text += "• 일주일 내로 종료되는 이벤트가 없습니다.\n\n"
            
        description_text += "**📌 진행 중**\n"
        if ongoing:
            description_text += "\n".join(ongoing)
        else:
            description_text += "• 진행 중인 이벤트가 없습니다."

        embed.description = description_text
        embed.set_footer(text=f"요청자: {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MapleCog(bot))