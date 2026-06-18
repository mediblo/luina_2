import discord
from discord.ext import commands
from discord import app_commands

from utils.http_client import get_json

from config.settings import riot_api
from utils.embed_builder import build_simple_embed

class RiotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.riot_emoji = []

    async def cog_load(self):
        self.riot_emoji = await self.bot.fetch_application_emojis()

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
            "NONE": ""
        }
        CHAMPION_RENAME = {
            'FiddleSticks' : 'Fiddlesticks'
        }
        
        api_url=f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{nickname[0]}/{nickname[1]}?api_key={riot_api}" # puuid 구하기 [account-v1]
        api_data = await get_json(api_url)

        if api_data.get('status', {}).get('status_code') == 404:
            await interaction.followup.send(content="유저를 찾을 수 없습니다. 닉네임과 태그를 정확히 입력했는지 확인해주세요.", ephemeral=True)
            return

        puuid = api_data['puuid']
        name = f"{api_data['gameName']}#{api_data['tagLine']}"
        api_url = f"https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={riot_api}"
        api_data = await get_json(api_url)
        profile_icon = api_data['profileIconId']

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
            if champion in CHAMPION_RENAME:
                champion = CHAMPION_RENAME[champion]
            champion_name_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver[0]}/data/ko_KR/champion/{champion}.json"
            champion_name = await get_json(champion_name_url)

            queue_id = api_data['info']['queueId']

            if mode != -1 and queue_id != mode: # 모드 선택 시 해당 모드만
                continue

            m_data['queueId'] = queue_id # 게임 모드
            m_data['win'] = api_data['info']['participants'][match_player_num]['win'] # 승패 여부
            # m_data['champion'] = champion_name['data'][champion]['name'] # 챔피언 이름
            m_data['champion'] = discord.utils.get(self.riot_emoji, name=champion) # 챔피언 emoji
            m_data['kill'] = api_data['info']['participants'][match_player_num]['kills'] # 킬
            m_data['death'] = api_data['info']['participants'][match_player_num]['deaths'] # 뎃
            m_data['assist'] = api_data['info']['participants'][match_player_num]['assists'] # 어시
            m_data['position'] = api_data['info']['participants'][match_player_num]['teamPosition'] # 포지션 [ 아레나, 칼바람은? ]
            
            match_data.append(m_data)
            if len(match_data) == 10:
                break

        
        total_games = len(match_data)

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
        embed.set_footer(text=f"OP.GG  •  Riot Games 제공")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

#########################################################################################################

    @app_commands.command(name="롤", description="해당 유저의 정보를 확인합니다.") # 롤 ??? / 240313 / 260618
    @app_commands.describe(nickname="태그 포함")
    async def lol_info(self, interaction: discord.interactions, nickname:str):
        await interaction.response.defer(ephemeral=True)
        nickname = nickname.split('#')
        TIER_MAP = {}
        RANK_MAP = {}

        CHAMPION_RENAME = {
            'FiddleSticks' : 'Fiddlesticks'
        }

        api_url=f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{nickname[0]}/{nickname[1]}?api_key={riot_api}" # puuid 구하기 [account-v1]
        api_data = await get_json(api_url)

        if api_data.get('status', {}).get('status_code') == 404:
            await interaction.followup.send(content="유저를 찾을 수 없습니다. 닉네임과 태그를 정확히 입력했는지 확인해주세요.", ephemeral=True)
            return

        puuid = api_data['puuid']
        name = f"{api_data['gameName']}#{api_data['tagLine']}"
        api_url = f"https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={riot_api}"
        api_data = await get_json(api_url)
        profile_icon = api_data['profileIconId']

        # most 3 [ champion-mastery-v4 ]
        api_url = f"https://kr.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=3&api_key={riot_api}"
        api_data = await get_json(api_url)

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
        api_url = f"https://kr.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}?api_key={riot_api}"
        api_data = await get_json(api_url)

        rank={}
        for data in api_data:
            dummy_data={}
            dummy_data['tier'] = data['tier']
            dummy_data['rank'] = data['rank']
            dummy_data['point'] = data['leaguePoints']
            dummy_data['win'] = data['wins']
            dummy_data['lose'] = data['losses']

            rank['SOLO' if data['queueType'] == 'RANKED_SOLO_5x5' else 'FLEX'] = dummy_data

        embed=build_simple_embed(
            title=name,
            description="test"
        )
        embed.set_author(name= name, url=f"https://op.gg/lol/summoners/kr/{name.replace('#', '-').replace(' ', '%20')}",
                         icon_url=f"https://ddragon.leagueoflegends.com/cdn/{game_ver[0]}/img/profileicon/{profile_icon}.png")

        field_value = ""
        for data in most_data:
            field_value += f"{discord.utils.get(self.riot_emoji, name=data['name'])} : {data['level']}Lv ({format(data['point'], ',')}점)\n"
        embed.add_field(name="모스트 3", value=field_value, inline=False)

        embed.add_field(name="개인/2인 랭크",
                       value=f"{discord.utils.get(self.riot_emoji, name=rank['SOLO']['tier'])} {rank['SOLO']['rank']} {rank['SOLO']['point']}점\n" + 
                                f"{rank['SOLO']['win'] + rank['SOLO']['lose']}전 {rank['SOLO']['win']}승 {rank['SOLO']['lose']}패 {(rank['SOLO']['win'] / (rank['SOLO']['win'] + rank['SOLO']['lose']) * 100):.2f}%")
        
    
        
        
        if rank.get('FLEX', False):
            embed.add_field(name="자유 랭크",
                           value=f"{discord.utils.get(self.riot_emoji, name=rank['FLEX']['tier'])} {rank['FLEX']['rank']} {rank['FLEX']['point']}점\n" + 
                                f"{rank['FLEX']['win'] + rank['FLEX']['lose']}전 {rank['FLEX']['win']}승 {rank['FLEX']['lose']}패 {(rank['FLEX']['win'] / (rank['FLEX']['win'] + rank['FLEX']['lose']) * 100):.2f}%")
        
        
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RiotCog(bot))