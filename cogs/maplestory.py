import discord, asyncio
from discord.ext import commands
from discord import app_commands

import json
import os
from config.settings import MAPLESTORY_API
from utils.http_client import get_json
from utils.embed_builder import build_simple_embed
from datetime import datetime

class MapleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_nickname = None
        self.headers= {
            'accept': 'application/json',
            'x-nxopen-api-key' : MAPLESTORY_API
        }
        self.time = datetime.now().strftime("%Y-%m-%d")
        self.file_path = 'data/maple_nickname.json'
        
    async def cog_load(self):
        if not os.path.exists(self.file_path): # 없음 만들기
            with open(self.file_path, 'w') as json_f:
                json.dump({}, json_f)

        with open(self.file_path, 'r') as json_f:
            self.user_nickname = json.load(json_f)

#########################################################################################################

    @app_commands.command(name="메이플_등록", description="해당 닉네임을 등록합니다.") # 메이플_등록 260701
    @app_commands.describe(닉네임="닉네임 (필수)")
    async def maple_add(self, interaction: discord.Interaction, 닉네임:str):
        if interaction.guild.id not in [1307325561890406452, 736512667530821653]:
            await interaction.response.send_message('개발중인 명령어 입니다.', ephemeral=True)
            return
        if self.user_nickname.get(닉네임):
            await interaction.response.send_message('이미 등록한 닉네임입니다.', ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        data_url = f'https://open.api.nexon.com/maplestory/v1/id?character_name={닉네임}'
        
        api_data:dict = await get_json(url=data_url, headers=self.headers)
        
        if api_data.get('ocid') is None: # 없는 이름
            await interaction.followup.send('없는 닉네임')
            return
        
        self.user_nickname[닉네임] = api_data['ocid']

        with open(self.file_path, 'w') as json_f:
            json.dump(self.user_nickname, json_f)

        await interaction.followup.send('등록 완료!')

#########################################################################################################

    @app_commands.command(name="메이플_랭킹", description="등록된 닉네임들의 랭킹을 조회합니다.") # 메이플_랭킹 260701
    async def maple_ranking(self, interaction: discord.Interaction):
        if interaction.guild.id not in [1307325561890406452, 736512667530821653]:
            await interaction.response.send_message('개발중인 명령어 입니다.', ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        stat_url = 'https://open.api.nexon.com/maplestory/v1/character/stat?ocid='
        rank_url = f'https://open.api.nexon.com/maplestory/v1/ranking/overall?date={self.time}&world_name=%EC%B1%8C%EB%A6%B0%EC%A0%80%EC%8A%A4&ocid='

        data=dict()
        for nickname, ocid in self.user_nickname.items():
            stat_api = await get_json(url=(stat_url+ocid), headers=self.headers)
            rank_api = await get_json(url=(rank_url+ocid), headers=self.headers)
            rank_api['ranking'][0]['power'] = stat_api['final_stat'][-2]['stat_value']
            data[rank_api['ranking'][0]['ranking']] = rank_api
            await asyncio.sleep(0.5)

        # 1. 딕셔너리의 Key(랭킹 번호)를 기준으로 오름차순(1등부터) 정렬
        sorted_ranking = sorted(data.items())

        # 2. 디스코드 임베드 생성
        embed = build_simple_embed(
            title="🍁 챌린저스 월드 캐릭터 랭킹",
            description=f"조회 기준일: `{self.time}`\n등록된 캐릭터들의 랭킹 정보입니다."
        )

        # 3. 정렬된 데이터를 돌며 임베드에 필드 추가
        for rank, rank_info in sorted_ranking:
            rank_val = int(rank)
            format_rank = f"{rank_val:,}"
            # ranking 리스트 안의 첫 번째 캐릭터 정보 추출
            char_data = rank_info['ranking'][0]
            
            name = char_data['character_name']
            level = char_data['character_level']
            job = char_data['class_name']
            guild = char_data['character_guildname'] or "없음"
            
            # 전투력(str -> int 변환 후 천 단위 쉼표 추가)
            power_val = int(char_data['power'])
            formatted_power = f"{power_val:,}"

            # 상위 3명에게는 특별한 이모지 부여 (시각적 효과)
            if rank == sorted_ranking[0][0]:
                rank_emoji = "🥇"
            elif len(sorted_ranking) > 1 and rank == sorted_ranking[1][0]:
                rank_emoji = "🥈"
            elif len(sorted_ranking) > 2 and rank == sorted_ranking[2][0]:
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
                name=f"{rank_emoji} {format_rank}위 - {name}",
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

    @app_commands.command(name="메이플_조회", description="해당 닉네임의 정보를 조회합니다.") # 메이플_조회 260701
    @app_commands.describe(닉네임="닉네임 (필수)")
    @app_commands.describe(공개여부="공개 여부를 선택합니다 (기본값 : 공개)")
    @app_commands.choices(공개여부=[
        app_commands.Choice(name="공개", value=1),
        app_commands.Choice(name="비공개", value=0)
    ])
    async def maple_search(self, interaction: discord.Interaction, 닉네임:str, 공개여부: int = 1):
        공개여부 = 공개여부 == 0  # 공개 여부를 boolean으로 변환

        await interaction.response.defer(ephemeral=공개여부)

        if (ocid:= self.user_nickname.get('닉네임')) is None:

            data_url = f'https://open.api.nexon.com/maplestory/v1/id?character_name={닉네임}'
            
            api_data:dict = await get_json(url=data_url, headers=self.headers)
            
            if api_data.get('ocid') is None: # 없는 이름
                await interaction.followup.send('없는 닉네임')
                return

            ocid = api_data['ocid']

        api_url = f'https://open.api.nexon.com/maplestory/v1/character/basic?ocid={ocid}'
        api_data:dict = await get_json(url=data_url, headers=self.headers)

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
        filled_blocks = int(exp_rate // 10)
        empty_blocks = 10 - filled_blocks
        exp_bar = "■" * filled_blocks + "□" * empty_blocks

        # 1. 임베드 기본 설정 (제목, 설명, 색상)
        embed = build_simple_embed(
            title=f"🍁 {name} (Lv.{level})",
            description=f"**{world} 월드**의 {job} 정보입니다."
        )

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
        embed.set_footer(text="Nexon Open API | MapleStory")

        return embed
        
async def setup(bot):
    await bot.add_cog(MapleCog(bot))