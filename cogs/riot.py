import discord, asyncio
from discord.ext import commands
from discord import app_commands
from typing import Optional
import json
from aiolimiter import AsyncLimiter
import time

from utils.http_client import get_json, get_response
from config.settings import RIOT_API
from utils.embed_builder import build_simple_embed

class RateLimitError(Exception):
    def __init__(self, wait_time):
        self.wait_time = wait_time

class RiotCog(commands.Cog):
    def __init__(self, bot):
        self.limiter = AsyncLimiter(max_rate=100, time_period=120)
        self.bot = bot
        self.riot_emoji = []
        self.CHAM_ABBR_MAP = {
            '갱플' : '갱플랭크', '그가' : '그라가스', '그브' : '그레이브즈',
            '노틸' : '노틸러스', '누누' : '누누와 윌럼프', '다리' : '다리우스',
            '드븐' : '드레이븐', '레나타' : '레나타 글라스크', '레넥' : '레넥톤',
            '리산' : '리산드라', '마이' : '마스터 이', '마오' : '마오카이',
            '말파' : '말파이트', '모데' : '모데카이저', '몰가' : '모르가나',
            '문도' : '문도 박사', '미포' : '미스 포츈', '볼베' : '볼리베어',
            '브라' : '브라이어', '블라디' : '블라디미르', '블미' : '블라디미르',
            '블츠' : '블리츠크랭크', '블랭' : '블리츠크랭크', '사일' : '사일러스',
            '세주' : '세주아니', '신짜오' : '신 짜오', '리신' : '리 신',
            '쓸쉬' : '쓰레쉬', '아우솔' : '아우렐리온 솔', '아트' : '아트록스',
            '아펠' : '아펠리오스', '알리' : '알리스타', '야소' : '야스오',
            '오리' : '오리아나', '이렐' : '이렐리아', '이즈' : '이즈리얼',
            '일라' : '일라오이', '자르반' : '자르반 4세', '카시' : '카시오페아',
            '카타' : '카타리나', '칼리' : '칼리스타', '케틀' : '케이틀린',
            '킨드' : '킨드레드', '탐켄치' : '탐 켄치', '켄치' : '탐 켄치',
            '트타' : '트리스타나', '트리' : '트리스타나', '트린' : '트린다미어',
            '트페' : '트위스티드 페이트', '트위스티드페이트' : '트위스티드 페이트',
            '피들' : '피들스틱', '하딩' : '하이머딩거' }

    async def cog_load(self):
        self.riot_emoji = await self.bot.fetch_application_emojis() # 이모지 불러오기
        api_url = f'https://kr.api.riotgames.com/lol/status/v4/platform-data?api_key={RIOT_API}'
        api_data = await get_response(api_url)
        status = api_data.status_code

        if 200 <= status < 300:
            print(f"🟢 Riot Games (KR) | Status: {status} (정상 연결)")
        
        # 🟡 노랑 동그라미: 호출 제한 초과 (429) 또는 일시적 서버 에러 (500대)
        elif status == 429 or status >= 500:
            print(f"🟡 Riot Games (KR) | Status: {status} (호출 제한 또는 서버 지연)")
        
        # 🔴 빨강 동그라미: 인증 실패 (401, 403) 및 기타 잘못된 요청 (400대)
        else:
            print(f"🔴 Riot Games (KR) | Status: {status} (인증 실패 또는 잘못된 요청)")

    def _check_rate_limit(self):
        """
        Riot API Rate Limit을 체크하는 공통 헬퍼 메서드.
        제한에 걸렸다면 정확한 대기 시간을 계산해 RateLimitError를 발생시킵니다.
        """
        if not self.limiter.has_capacity():
            # 현재 이벤트 루프 시간 기준 계산
            current_time = self.limiter._loop.time()
            wait_time = self.limiter._rate_limit_per_item - (current_time - self.limiter._last_check)
            
            # 타이머 오차 방지용 보정 계산
            if wait_time <= 0:
                wait_time = max(0.1, self.limiter.time_period - (time.time() % self.limiter.time_period))
            
            raise RateLimitError(wait_time)
        
    async def request_api(self, interaction, url):
        try:
            # 1. 제한 체크
            self._check_rate_limit()
            
            # 2. 토큰 소모 및 API 호출
            async with self.limiter:
                return await get_json(url)
                
        except RateLimitError as r:
            # 3. 제한에 걸리면 여기서 알아서 디스코드 메시지를 보내줍니다.
            await interaction.followup.send(
                f"🛑 [제한 도달] Riot API 요청 제한에 도달했습니다.\n약 {r.wait_time:.1f}초 후에 다시 시도해 주세요."
            )
            # 제한에 걸렸음을 호출한 쪽에 알리기 위해 특별한 값(None이나 False) 리반환
            return "RATE_LIMITED"

#########################################################################################################

    async def _fetch_match_data(self, match_id):
        api_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={RIOT_API}"
        # limiter가 알아서 내부적으로 큐를 관리하며 속도를 조절합니다.
        try:
            # 1. 분리한 함수로 레이트 리밋 검사 (제한 시 여기서 바로 RateLimitError 발생)
            self._check_rate_limit()
            
            # 2. 자리가 있다면 바로 통과하여 토큰 소모 및 API 호출
            async with self.limiter:
                return await get_json(api_url)
                
        except RateLimitError:
            # RateLimitError는 상위(gather 호출부)에서 처리할 수 있도록 그대로 위로 던짐(raise)
            raise
        except Exception as e:
            # 일반적인 네트워크 에러나 API 에러는 로깅 후 None 반환
            print(f"Match {match_id} fetch error: {e}")
            return None

    @app_commands.command(name="전적", description="해당 유저의 최근 10판을 확인합니다.") # 전적 201212 / 220808 / 260618
    @app_commands.describe(닉네임="태그 포함")                                          # 총 23번
    @app_commands.choices(
        모드=[ # 신속, 일반, 솔랭, 자랭, 칼바람, 아레나
            app_commands.Choice(name="신속", value=490),
            app_commands.Choice(name="일반", value=400),
            app_commands.Choice(name="개인/2인 랭크", value=420),
            app_commands.Choice(name="자유 랭크", value=440),
            app_commands.Choice(name="칼바람", value=450),
            app_commands.Choice(name="증바람", value=2400),
            app_commands.Choice(name="아레나", value=1750),
        ] 
    )
    @app_commands.describe(공개여부="공개 여부 (기본값: 공개)")
    @app_commands.choices(
        공개여부=[
            app_commands.Choice(name="공개", value=1),
            app_commands.Choice(name="비공개", value=0)
        ]
    )
    async def match_log(self, interaction: discord.Interaction, 닉네임:str, 모드:int = -1, 공개여부: int = 1):
        공개여부 = 공개여부 == 0  # 공개 여부를 boolean으로 변환
        await interaction.response.defer(ephemeral=공개여부)
        nickname = 닉네임.split('#')
        mode = 모드

        QUEUE_DATA = {
            400 : "일반",
            420 : "솔랭",
            440 : "자랭",
            450 : "칼바람",
            490 : "신속",
            1750 : "아레나",
            2400 : "증바람"
        }
        POSITION_MAP = {
            "TOP": "탑",
            "JUNGLE": "정글",
            "MIDDLE": "미드",
            "BOTTOM": "원딜",
            "UTILITY": "서포터",
            "NONE": ""
        }
        CHAMPION_RENAME = {
            'FiddleSticks' : 'Fiddlesticks'
        }
        
        # 닉네임 형식 예외 처리 (태그 누락 방지)
        if len(nickname) < 2:
            await interaction.followup.send(content="닉네임에 태그(#)를 포함해 주세요. (예: 닉네임#KR1)", ephemeral=True)
            return

        api_url=f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{nickname[0]}/{nickname[1]}?api_key={RIOT_API}" # puuid 구하기 [account-v1]
        api_data = await self.request_api(interaction, api_url)
        if api_data == "RATE_LIMITED": 
            return
        

        if api_data.get('status', {}).get('status_code') == 404:
            await interaction.followup.send(content="유저를 찾을 수 없습니다. 닉네임과 태그를 정확히 입력했는지 확인해주세요.", ephemeral=True)
            return

        puuid = api_data['puuid']
        name = f"{api_data['gameName']}#{api_data['tagLine']}"

        api_url = f"https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={RIOT_API}"
        api_data = await self.request_api(interaction, api_url)
        if api_data == "RATE_LIMITED": 
            return
        
        profile_icon = api_data['profileIconId']

        api_url=f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=20&api_key={RIOT_API}" # 매치id 구하기 [match-v5]
        matchs = await self.request_api(interaction, api_url)
        if api_data == "RATE_LIMITED": 
            return

        if not matchs:
            await interaction.followup.send("최근 플레이한 전적이 없습니다.", ephemeral=True)
            return

        tasks = [self._fetch_match_data(match_id) for match_id in matchs] # 병렬 매치 불러오기
        all_match_responses = await asyncio.gather(*tasks, return_exceptions=True)

        for res in all_match_responses:
            if isinstance(res, RateLimitError):
                # 제한에 걸린 첫 번째 태스크의 남은 시간을 가져와 메시지 전송
                await interaction.followup.send(
                    f"🛑 [제한 도달] Riot API 요청 제한에 도달했습니다.\n약 {res.wait_time:.1f}초 후에 다시 시도해 주세요."
                )
                return  # 명령어 수행 중단

        match_data = []
        wins = 0

        # 병렬로 받아온 결과들을 순차 처리 및 데이터 가공
        for api_data in all_match_responses:
            # 예외 객체거나, 데이터를 받지 못했거나, 올바르지 않은 응답 패스
            if isinstance(api_data, Exception) or not api_data or 'info' not in api_data:
                continue

            # 예기치 않은 중단 [ 다시하기 등 ] 패스
            if api_data['info'].get('endOfGameResult') == 'Abort_Unexpected':
                continue
            
            # 특정 모드 선택 시 매칭 검사
            queue_id = api_data['info']['queueId']
            if mode != -1 and queue_id != mode:
                continue

            try:
                # 플레이어 인덱스 번호 찾기
                match_player_num = api_data['metadata']['participants'].index(puuid)
            except (ValueError, KeyError):
                continue
            
            player_info = api_data['info']['participants'][match_player_num]
            
            champion = player_info['championName']
            if champion in CHAMPION_RENAME:
                champion = CHAMPION_RENAME[champion]

            m_data = {
                'queueId': queue_id,
                'win': player_info['win'],
                'champion': discord.utils.get(self.riot_emoji, name=champion),
                'kill': player_info['kills'],
                'death': player_info['deaths'],
                'assist': player_info['assists'],
                'position': player_info['teamPosition']
            }
            
            match_data.append(m_data)
            
            # 최종 정제된 유효 데이터가 10개가 쌓이면 즉시 중단
            if len(match_data) == 10:
                break

        total_games = len(match_data)
        if total_games == 0:
            await interaction.followup.send("조건에 맞는 최근 전적이 없습니다.", ephemeral=True)
            return

        embed = build_simple_embed(
            title= "리그 오브 레전드 전적",
            description=None
        )

        for i, match in enumerate(match_data):
            queue_name = QUEUE_DATA.get(match.get('queueId'), "기타 모드")
            is_win = match.get('win')
            
            # 승패 기호 및 텍스트 설정
            if is_win:
                wins += 1
                result_emoji = "🔵"
                result_text = "승리"
            else:
                result_emoji = "🔴"
                result_text = "패배"
                
            champion = match.get('champion', 'Unknown')
            k = match.get('kill', 0)
            d = match.get('death', 0)
            a = match.get('assist', 0)
            position = POSITION_MAP.get(match.get('position'), "")
            if position:
                position = discord.utils.get(self.riot_emoji, name=match['position'])
            
            # KDA 평점 계산
            if d == 0:
                kda_ratio = "Perfect"
            else:
                kda_ratio = round((k + a) / d, 2)
                
            # 개별 게임 정보 텍스트 포맷팅
            field_name = f"{result_emoji} {queue_name} | {result_text}"
            field_value = (
                f"**챔피언:** {champion}  {position}\n"
                f"**KDA:** {k} / {d} / {a}   [ 평점: {kda_ratio} ]"
            )

            embed.add_field(name=field_name, value=field_value)
            if (i+1) % 2 == 0:
                embed.add_field(name="\u200b", value="\u200b", inline=False)  # 빈 필드 추가 (줄바꿈 용)
        
        if len(match_data) == 0:
            await interaction.followup.send("최근 플레이한 전적이 없습니다.", ephemeral=True)
            return
        
        # 종합 승률 계산 후 임베드 설명(description)에 상단 고정
        win_rate = int((wins / total_games) * 100)

        embed.description = f"**최근{' ' + QUEUE_DATA.get(mode, '')} {total_games}전 {wins}승 {total_games - wins}패 (승률 {win_rate}%)**\n" + ("-" * 30)

        embed.set_author(name= name, url=f"https://op.gg/lol/summoners/kr/{name.replace('#', '-').replace(' ', '%20')}",
                         icon_url=f"https://ddragon.leagueoflegends.com/cdn/16.12.1/img/profileicon/{profile_icon}.png")
        embed.set_footer(text=f"OP.GG로 이동  •  Riot Games 제공")
        
        await interaction.followup.send(embed=embed, ephemeral=공개여부)

#########################################################################################################

    @app_commands.command(name="롤", description="해당 유저의 정보를 확인합니다.") # 롤 ??? / 240313 / 260619
    @app_commands.describe(닉네임="태그 포함")                                  # 총 4번
    @app_commands.describe(공개여부="공개 여부 (기본값: 공개)")
    @app_commands.choices(
        공개여부=[
            app_commands.Choice(name="공개", value=1),
            app_commands.Choice(name="비공개", value=0)
        ]
    )
    async def lol_info(self, interaction: discord.Interaction, 닉네임:str, 공개여부: int = 1):
        nickname = 닉네임.split('#')
        TIER_MAP = {'IRON' : 'I', 'BRONZE' : 'B', 'SILVER' : 'S',
                    'GOLD' : 'G', 'PLATINUM' : 'P', 'EMERALD' : 'E',
                    'DIAMOND' : 'D', 'MASTER' : 'M', 'GRANDMASTER' : 'GM',
                    'CHALLENGER' : 'C'}
        RANK_MAP = { 'I':'1', 'II' : '2', 'III' : '3', 'IV' : '4', '':'' }

        CHAMPION_RENAME = {
            'FiddleSticks' : 'Fiddlesticks'
        }
        공개여부 = 공개여부 == 0  # 공개 여부를 boolean으로 변환
        await interaction.response.defer(ephemeral=공개여부)

        api_url=f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{nickname[0]}/{nickname[1]}?api_key={RIOT_API}" # puuid 구하기 [account-v1]
        api_data = await self.request_api(interaction, api_url)
        if api_data == "RATE_LIMITED": 
            return
        

        if api_data.get('status', {}).get('status_code') == 404:
            await interaction.followup.send(content="유저를 찾을 수 없습니다. 닉네임과 태그를 정확히 입력했는지 확인해주세요.")
            return

        puuid = api_data['puuid']
        name = f"{api_data['gameName']}#{api_data['tagLine']}"


        api_url = f"https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={RIOT_API}"
        api_data = await self.request_api(interaction, api_url)
        if api_data == "RATE_LIMITED": 
            return


        profile_icon = api_data['profileIconId']
        player_level = api_data['summonerLevel']

        # most 3 [ champion-mastery-v4 ]
        api_url = f"https://kr.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=3&api_key={RIOT_API}"
        api_data = await self.request_api(interaction, api_url)
        if api_data == "RATE_LIMITED": 
            return

        most_data=[]
        for data in api_data:
            dummy_data = {}

            dummy_data['id'] = data['championId']
            dummy_data['level'] = data['championLevel']
            dummy_data['point'] = data['championPoints']
            
            most_data.append(dummy_data)

        game_ver_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        game_ver = await get_json(game_ver_url)

        champion_data_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver[0]}/data/ko_KR/champion.json"
        champion_data = await get_json(champion_data_url)
        
        flag = 0
        for val in champion_data['data'].values():
            if flag == 3:
                break
            for data in most_data:
                if str(data['id']) == val['key']:
                    flag+=1
                    data['name'] = val['id']

        # 솔랭 자랭 [ league-v4 ]
        api_url = f"https://kr.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}?api_key={RIOT_API}"
        api_data = await self.request_api(interaction, api_url)
        if api_data == "RATE_LIMITED": 
            return

        rank={}
        for data in api_data:
            dummy_data={}
            dummy_data['tier'] = data['tier']
            dummy_data['rank'] = data['rank'] if dummy_data['tier'] not in ['MASTER', 'GRANDMASTER', 'CHALLENGER'] else ''
            dummy_data['point'] = data['leaguePoints']
            dummy_data['win'] = data['wins']
            dummy_data['lose'] = data['losses']

            rank['SOLO' if data['queueType'] == 'RANKED_SOLO_5x5' else 'FLEX'] = dummy_data

        embed=build_simple_embed(
            title='리그 오브 레전드 유저 정보',
            description="-# 닉네임 클릭 시 OP.GG로 넘어갑니다."
        )
        embed.set_author(name= f"{name} Lv.{player_level}", url=f"https://op.gg/lol/summoners/kr/{name.replace('#', '-').replace(' ', '%20')}",
                         icon_url=f"https://ddragon.leagueoflegends.com/cdn/{game_ver[0]}/img/profileicon/{profile_icon}.png")

        field_value = ""
        for data in most_data:
            field_value += f"{discord.utils.get(self.riot_emoji, name=data['name'])} : {data['level']}Lv ({format(data['point'], ',')}점)\n"
        embed.add_field(name="모스트 3", value=field_value, inline=False)

        if rank.get('SOLO', False):
            embed.add_field(name=f"개인/2인 랭크 {TIER_MAP[rank['SOLO']['tier']]}{RANK_MAP[rank['SOLO']['rank']]}",
                        value=f"{discord.utils.get(self.riot_emoji, name=rank['SOLO']['tier'])} {rank['SOLO']['rank']} {rank['SOLO']['point']}점\n" + 
                                    f"{rank['SOLO']['win'] + rank['SOLO']['lose']}전 {rank['SOLO']['win']}승 {rank['SOLO']['lose']}패 {(rank['SOLO']['win'] / (rank['SOLO']['win'] + rank['SOLO']['lose']) * 100):.2f}%")
        
        if rank.get('FLEX', False):
            embed.add_field(name=f"자유 랭크 {TIER_MAP[rank['FLEX']['tier']]}{RANK_MAP[rank['FLEX']['rank']]}",
                           value=f"{discord.utils.get(self.riot_emoji, name=rank['FLEX']['tier'])} {rank['FLEX']['rank']} {rank['FLEX']['point']}점\n" + 
                                f"{rank['FLEX']['win'] + rank['FLEX']['lose']}전 {rank['FLEX']['win']}승 {rank['FLEX']['lose']}패 {(rank['FLEX']['win'] / (rank['FLEX']['win'] + rank['FLEX']['lose']) * 100):.2f}%")
        
        embed.set_footer(text=f"OP.GG로 이동  •  Riot Games 제공")
        await interaction.followup.send(embed=embed)

#########################################################################################################

    @app_commands.command(name="롤챔프", description="해당 챔피언의 스킬 정보를 확인합니다.") # 롤 챔피언 210105 / 240313 / 260619 / 260622
    @app_commands.describe(챔피언="챔피언 이름")
    @app_commands.describe(공개여부="공개 여부 (기본값: 공개)")
    @app_commands.choices(
        공개여부=[
            app_commands.Choice(name="공개", value=1),
            app_commands.Choice(name="비공개", value=0)
        ]
    )
    async def cham_info(self, interaction: discord.Interaction, 챔피언:str, 공개여부: int = 1):
        공개여부 = 공개여부 == 0  # 공개 여부를 boolean으로 변환

        champion = self.CHAM_ABBR_MAP.get(챔피언, 챔피언)

        await interaction.response.defer(ephemeral=공개여부)

        game_ver_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        game_ver = (await get_json(game_ver_url))[0]

        champion_data_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver}/data/ko_KR/champion.json" # 이름 찾기
        champion_data = await get_json(champion_data_url)
        
        champion_id = ""
        for val in champion_data['data'].values():
            if str(champion) == val['name']:
                champion_id = val['id']
                break

        if not champion_id: # 오타, 없는 챔피언
            await interaction.followup.send("해당하는 챔피언의 정보가 없습니다!")
            return

        champion_data_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver}/data/ko_KR/champion/{champion_id}.json"
        champion_data = await get_json(champion_data_url)

        embed = build_simple_embed(
            title= champion,
            description="스킬 정보입니다."
        )
        champion_url = f"https://op.gg/ko/lol/champions/{champion_id}/build"
        embed.url = champion_url

        thumbnail_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver}/img/champion/{champion_id}.png"
        embed.set_thumbnail(url = thumbnail_url)

        passive = champion_data['data'][champion_id]['passive']
        passive_value = passive['description'].replace('<br>', '\n> ')
        embed.add_field(
            name=f"{discord.utils.get(self.riot_emoji, name=passive['image']['full'][:-4])}   패시브 - {passive['name']}",
            value=f"> {passive_value}\n",
            inline=False
        )

        spells = champion_data['data'][champion_id]['spells']
        # 3. Q, W, E, R 스킬 정보 반복문으로 추가
        skill_keys = ["Q", "W", "E", "R"]
        for i, spell in enumerate(spells):
            costBurn = spell['costType'] if spell['costType'] == '소모값 없음' else spell['costBurn']
            if costBurn == "0":
                costBurn = '소모값 없음'

            spell_value = spell['description'].replace('<br>', '\n> ')
            embed.add_field(
                name=f"{discord.utils.get(self.riot_emoji, name=spell['image']['full'][:-4])}   {skill_keys[i]} - {spell['name']}",
                value=f"> {spell_value}\n"
                    f"⏱️ **쿨타임:** {spell['cooldownBurn'].replace('/', ' / ')}초 |"
                    f"💧 **소모:** {costBurn}",
                inline=False
            )

        embed.set_footer(text=f"OP.GG로 이동  •  Riot Games 제공")
        
        view=chamBtn(interaction=interaction, champion=champion, data=champion_data, game_ver=game_ver, id=champion_id, riot_emoji=self.riot_emoji)
        await interaction.followup.send(embed=embed, view=view)

#########################################################################################################

    @app_commands.command(name="스킬가속", description="해당 챔피언의 스킬 가속를 확인합니다.") # 스킬가속 계산기 260622
    @app_commands.describe(챔피언="챔피언 이름")
    @app_commands.describe(스킬가속="스킬가속")
    @app_commands.describe(상대챔피언="상대 챔피언 이름 (선택사항)")
    @app_commands.describe(상대스킬가속="상대 스킬가속 (선택사항)")
    @app_commands.describe(공개여부="공개 여부 (기본값: 공개)")
    @app_commands.choices(
        공개여부=[
            app_commands.Choice(name="공개", value=1),
            app_commands.Choice(name="비공개", value=0)
        ]
    )
    async def cdr_cal(self, interaction: discord.Interaction, 챔피언:str, 스킬가속:int,
                        상대챔피언:Optional[str]=None, 상대스킬가속:Optional[int]=None,
                        공개여부: int = 1):
        공개여부 = 공개여부 == 0  # 공개 여부를 boolean으로 변환
        enemy_flag = False
        champion = self.CHAM_ABBR_MAP.get(챔피언, 챔피언)
        cooldown_reduction = 스킬가속
        enemy_cooldown_reduction = 상대스킬가속
        if 상대챔피언:
            enemy_champion = self.CHAM_ABBR_MAP.get(상대챔피언, 상대챔피언)
            enemy_flag = True
            if enemy_cooldown_reduction is None: # 스킬가속 입력 X 시
                await interaction.response.send_message("스킬가속을 입력해주세요!", ephemeral=True)
                return

        await interaction.response.defer(ephemeral=공개여부)
                        
        game_ver_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        game_ver = (await get_json(game_ver_url))[0]

        champion_data_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver}/data/ko_KR/champion.json" # 이름 찾기
        champion_data = await get_json(champion_data_url)
        
        champion_id = ""
        for val in champion_data['data'].values():
            if str(champion) == val['name']:
                champion_id = val['id']
                break

        if not champion_id: # 오타, 없는 챔피언
            await interaction.followup.send("해당하는 챔피언의 정보가 없습니다!")
            return
        
        enemy_champion_id =""
        if enemy_flag:
            for val in champion_data['data'].values():
                if str(enemy_champion) == val['name']:
                    enemy_champion_id = val['id']
                    break

            if not enemy_champion_id: # 오타, 없는 챔피언
                await interaction.followup.send("해당하는 상대 챔피언의 정보가 없습니다!")
                return

        embed = build_simple_embed(
            title= "스킬가속 계산기",
            description=""
        )

        champion_data_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver}/data/ko_KR/champion/{champion_id}.json"
        champion_data = await get_json(champion_data_url)

        spells = champion_data['data'][champion_id]['spells']

        cooldown=[]
        for spell in spells:
            cooldown.append([round(cd * (100 / (100 + cooldown_reduction)), 1) for cd in [float(x) for x in spell['cooldownBurn'].split('/')]])

        if enemy_flag:
            champion_data_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver}/data/ko_KR/champion/{enemy_champion_id}.json"
            champion_data = await get_json(champion_data_url)

            enemy_spells = champion_data['data'][enemy_champion_id]['spells']

            enemy_cooldown=[]
            for spell in enemy_spells:
                enemy_cooldown.append([round(cd * (100 / (100 + enemy_cooldown_reduction)), 1) for cd in [float(x) for x in spell['cooldownBurn'].split('/')]])
        
        slot_names = ['Q', 'W', 'E', 'R']

        # 내 스킬 정보 필드 추가
        my_text = f"**⚙️ 스킬 가속:** `{cooldown_reduction}`\n\n"
        for i, spell in enumerate(spells):
            # 리스트 형식 [10, 9, 8]을 '10 / 9 / 8' 문자열로 변환
            cd_str = " / ".join(map(str, cooldown[i]))
            my_text += f"{discord.utils.get(self.riot_emoji, name=spell['image']['full'][:-4])}   **{slot_names[i]} ({spell['name']})**\n> {cd_str}\n"

        embed.add_field(name=f"{discord.utils.get(self.riot_emoji, name=champion_id)} {champion}", value=my_text, inline=True)

        if enemy_flag:
            # 상대 스킬 정보 필드 추가
            enemy_text = f"**⚙️ 스킬 가속:** `{enemy_cooldown_reduction}`\n\n"
            for i, spell in enumerate(enemy_spells):
                enemy_cd_str = " / ".join(map(str, enemy_cooldown[i]))
                enemy_text += f"{discord.utils.get(self.riot_emoji, name=spell['image']['full'][:-4])}  **{slot_names[i]} ({spell['name']})**\n> {enemy_cd_str}\n"

            embed.add_field(name=f"{discord.utils.get(self.riot_emoji, name=enemy_champion_id)} {enemy_champion}", value=enemy_text, inline=True)
        
        embed.set_footer(text=f"Riot Games 제공")
        await interaction.followup.send(embed=embed)

#########################################################################################################

class chamBtn(discord.ui.View):
    def __init__(self, interaction: discord.Interaction | discord.Member, data:json, champion:str, game_ver:str, id:str, riot_emoji:list):
        super().__init__(timeout=10)
        self.interaction = interaction
        self.data = data
        self.champion = champion
        self.game_ver = game_ver
        self.id = id
        self.riot_emoji = riot_emoji
        self.embed = build_simple_embed(
                title= self.champion,
                description="스킬 및 능력치 상세 정보입니다."
            )
        thumbnail_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver}/img/champion/{id}.png"
        self.embed.set_thumbnail(url=thumbnail_url)

        champion_url = f"https://op.gg/ko/lol/champions/{id}/build"
        self.embed.url = champion_url
    
    async def on_timeout(self):
        # 1. view에 속한 모든 버튼을 반복문으로 돌며 비활성화(disabled)시킵니다.
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @discord.ui.button(label="상세 정보", style=discord.ButtonStyle.success)
    async def more_info_btn(self, interaction : discord.Interaction, btn : discord.ui.Button):
        stats = self.data['data'][self.id]['stats']

        self.embed.add_field(name="❤️ 체력 (HP)", value=f"`{stats['hp']}` (+{stats['hpperlevel']}/Lv)", inline=True)
        self.embed.add_field(name="💧 마나 (MP)", value=f"`{stats['mp']}` (+{stats['mpperlevel']}/Lv)", inline=True)
        self.embed.add_field(name="👟 이동 속도", value=f"`{stats['movespeed']}`", inline=True)

        self.embed.add_field(name="🛡️ 방어력", value=f"`{stats['armor']}` (+{stats['armorperlevel']}/Lv)", inline=True)
        self.embed.add_field(name="🔮 마법 저항력", value=f"`{stats['spellblock']}` (+{stats['spellblockperlevel']}/Lv)", inline=True)
        self.embed.add_field(name="⚔️ 공격력 (AD)", value=f"`{stats['attackdamage']}` (+{stats['attackdamageperlevel']}/Lv)", inline=True)

        self.embed.add_field(name="💚 체력 재생 (5초)", value=f"`{stats['hpregen']}` (+{stats['hpregenperlevel']}/Lv)", inline=True)
        self.embed.add_field(name="💙 마나 재생 (5초)", value=f"`{stats['mpregen']}` (+{stats['mpregenperlevel']}/Lv)", inline=True)
        self.embed.add_field(name="⚡ 공격 속도", value=f"`{stats['attackspeed']}` (+{stats['attackspeedperlevel']}%/Lv)", inline=True)

        passive = self.data['data'][self.id]['passive']
        passive_value = passive['description'].replace('<br>', '\n> ')
        self.embed.add_field(
            name=f"{discord.utils.get(self.riot_emoji, name=passive['image']['full'][:-4])}   패시브 - {passive['name']}",
            value=f"> {passive_value}\n",
            inline=False
        )

        spells = self.data['data'][self.id]['spells']
        # 3. Q, W, E, R 스킬 정보 반복문으로 추가
        skill_keys = ["Q", "W", "E", "R"]
        for i, spell in enumerate(spells):
            costBurn = spell['costType'] if spell['costType'] == '소모값 없음' else spell['costBurn']
            if costBurn == "0":
                costBurn = '소모값 없음'

            
            spell_value = spell['description'].replace('<br>', '\n> ')
            self.embed.add_field(
                name=f"{discord.utils.get(self.riot_emoji, name=spell['image']['full'][:-4])}   {skill_keys[i]} - {spell['name']}",
                value=f"> {spell_value}\n"
                    f"⏱️ **쿨타임:** {spell['cooldownBurn'].replace('/', ' / ')}초 |"
                    f"💧 **소모:** {costBurn}",
                inline=False
            )

        separator = "\\*" * 40
        self.embed.add_field(name="", value=f"**{separator}**", inline=False)
    
        # 아군 팁 줄바꿈 처리하여 문자열로 합성
        ally_tips_text = "\n".join([f"- {tip}" for tip in self.data['data'][self.id]['allytips']])
        self.embed.add_field(name="🔵 플레이할 때 (Ally Tips)", value=f"{ally_tips_text}", inline=False)

        # 적군 팁 줄바꿈 처리하여 문자열로 합성
        enemy_tips_text = "\n".join([f"- {tip}" for tip in self.data['data'][self.id]['enemytips']])
        self.embed.add_field(name="🔴 상대할 때 (Enemy Tips)", value=f"{enemy_tips_text}", inline=False)

        self.embed.set_footer(text=f"OP.GG로 이동  •  Riot Games 제공")
        await interaction.response.edit_message(embed=self.embed, view=None)

async def setup(bot):
    await bot.add_cog(RiotCog(bot))