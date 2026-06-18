import discord
from discord.ext import commands
from discord import app_commands

from utils.http_client import get_json

from config.settings import riot_api
from utils.embed_builder import build_simple_embed

class RiotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="전적", description="해당 유저의 최근 10판을 확인합니다.") # 전적 201212 / 220808 / 260618
    @app_commands.describe(nickname="태그 포함")
    @app_commands.choices(
        mode=[ # 신속, 일반, 솔랭, 자랭, 칼바람, 아레나
            app_commands.Choice(name="신속", value=490),
            app_commands.Choice(name="일반", value=400),
            app_commands.Choice(name="개인/2인 랭크", value=420),
            app_commands.Choice(name="자유 랭크", value=440),
            app_commands.Choice(name="칼바람", value=450),
            app_commands.Choice(name="증바람", value=2400),
            app_commands.Choice(name="아레나", value=1750),
        ] 
    )
    async def match_log(self, interaction: discord.interactions, nickname:str, mode:int = -1):
        await interaction.response.defer(ephemeral=True)
        nickname = nickname.split('#')
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
            "NONE": "기타"
        }
        
        api_url=f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{nickname[0]}/{nickname[1]}?api_key={riot_api}" # puuid 구하기 [account-v1]
        api_data = await get_json(api_url)

        if api_data.get('status', {}).get('status_code') == 404:
            await interaction.followup.send(content="유저를 찾을 수 없습니다. 닉네임과 태그를 정확히 입력했는지 확인해주세요.", ephemeral=True)
            return

        puuid = api_data['puuid']
        name = f"{api_data['gameName']}#{api_data['tagLine']}"

        api_url=f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=20&api_key={riot_api}" # 매치id 구하기 [match-v5]
        matchs = await get_json(api_url)

        match_data=[]
        wins = 0

        for match_id in matchs:
            m_data = {}
            api_url=f"https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={riot_api}" # 매치 정보 구하기 [match-v5]
            api_data = await get_json(api_url)

            if api_data['info']['endOfGameResult'] == 'Abort_Unexpected': # 예기치 않은 중단 [ 아마 다시하기 인듯 ]
                continue
            
            match_player_num = api_data['metadata']['participants'].index(puuid) # 플레이어 번호 [ 메타데이터 ]
            
            game_ver_url = "https://ddragon.leagueoflegends.com/api/versions.json"
            game_ver = await get_json(game_ver_url)
            champion = api_data['info']['participants'][match_player_num]['championName']
            champion_name_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver[0]}/data/ko_KR/champion/{champion}.json"
            champion_name = await get_json(champion_name_url)

            queue_id = api_data['info']['queueId']

            if mode != -1 and queue_id != mode: # 모드 선택 시 해당 모드만
                continue

            m_data['queueId'] = queue_id # 게임 모드
            m_data['win'] = api_data['info']['participants'][match_player_num]['win'] # 승패 여부
            m_data['champion'] = champion_name['data'][champion]['name'] # 챔피언 이름
            m_data['kill'] = api_data['info']['participants'][match_player_num]['kills'] # 킬
            m_data['death'] = api_data['info']['participants'][match_player_num]['deaths'] # 뎃
            m_data['assist'] = api_data['info']['participants'][match_player_num]['assists'] # 어시
            m_data['position'] = api_data['info']['participants'][match_player_num]['teamPosition'] # 포지션 [ 아레나, 칼바람은? ]
            
            match_data.append(m_data)
            if len(match_data) == 10:
                break

        
        total_games = len(match_data)

        embed = build_simple_embed(
            title= name,
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
            position = POSITION_MAP.get(match.get('position'), "기타")
            
            # KDA 평점 계산
            if d == 0:
                kda_ratio = "Perfect"
            else:
                kda_ratio = round((k + a) / d, 2)
                
            # 개별 게임 정보 텍스트 포맷팅
            field_name = f"{result_emoji} {queue_name} | {result_text}"
            field_value = (
                f"**챔피언:** {champion} ({position})\n"
                f"**KDA:** {k} / {d} / {a}   (평점: {kda_ratio})"
            )

            embed.add_field(name=field_name, value=field_value)
            if (i+1) % 2 == 0:
                embed.add_field(name="\u200b", value="\u200b", inline=False)  # 빈 필드 추가 (줄바꿈 용)
        
        if len(match_data) == 0:
            await interaction.followup.send("최근 플레이한 전적이 없습니다.", ephemeral=True)
            return
        
        # 종합 승률 계산 후 임베드 설명(description)에 상단 고정
        win_rate = int((wins / total_games) * 100)

        embed.url = f"https://op.gg/lol/summoners/kr/{name.replace('#', '-').replace(' ', '%20')}" # OP.GG 링크
        embed.description = f"**최근{' ' + QUEUE_DATA.get(mode, '')} {total_games}전 {wins}승 {total_games - wins}패 (승률 {win_rate}%)**\n" + ("-" * 30)
        embed.set_footer(text=f"OP.GG  •  Riot Games 제공")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # title 리그 오브 레전드 전적
        # author = 닉네임(opgg url), icon
        # 챔피언 와꾸 커스텀 이모지로 만들기 스발;


async def setup(bot):
    await bot.add_cog(RiotCog(bot))