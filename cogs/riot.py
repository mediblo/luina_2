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
        embed.set_footer(text=f"OP.GG로 이동  •  Riot Games 제공")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

#########################################################################################################

    @app_commands.command(name="롤", description="해당 유저의 정보를 확인합니다.") # 롤 ??? / 240313 / 260619
    @app_commands.describe(nickname="태그 포함")
    async def lol_info(self, interaction: discord.interactions, nickname:str):
        await interaction.response.defer(ephemeral=True)
        nickname = nickname.split('#')
        TIER_MAP = {'IRON' : 'I', 'BRONZE' : 'B', 'SILVER' : 'S',
                    'GOLD' : 'G', 'PLATINUM' : 'P', 'EMERALD' : 'E',
                    'DIAMOND' : 'D', 'MASTER' : 'M', 'GRANDMASTER' : 'GM',
                    'CHALLENGER' : 'C'}
        RANK_MAP = { 'I':'1', 'II' : '2', 'III' : '3', 'IV' : '4', '':'' }

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
        player_level = api_data['summonerLevel']

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
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="롤챔프", description="해당 챔피언의 정보를 확인합니다.") # 롤 챔피언 210105 / 240313 / 260619
    @app_commands.describe(champion="챔피언 이름")
    async def lol_info(self, interaction: discord.interactions, champion:str):
        CHAM_ABBR_MAP = {
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
        
        champion = CHAM_ABBR_MAP.get(champion, champion)

        game_ver_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        game_ver = (await get_json(game_ver_url))[0]

        champion_data_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver}/data/ko_KR/champion.json" # 이름 찾기
        champion_data = await get_json(champion_data_url)
        
        champion_id = ""
        champion_key = ""
        for val in champion_data['data'].values():
            if str(champion) == val['name']:
                champion_id = val['id']
                champion_key = val['key']
                break

        champion_data_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver}/data/ko_KR/champion/{champion_id}.json"
        champion_data = await get_json(champion_data_url)

        embed = build_simple_embed(
            title= champion,
            description="상세 능력치 및 스킬입니다."
        )
        champion_url = f"https://lol.ps/champ/{champion_key}"
        embed.url = champion_url

        thumbnail_url = f"https://ddragon.leagueoflegends.com/cdn/{game_ver}/img/champion/{champion_id}.png"
        embed.set_thumbnail(url = thumbnail_url)

        stats = champion_data['data'][champion_id]['stats']

        embed.add_field(name="❤️ 체력 (HP)", value=f"`{stats['hp']}` (+{stats['hpperlevel']}/Lv)", inline=True)
        embed.add_field(name="💧 마나 (MP)", value=f"`{stats['mp']}` (+{stats['mpperlevel']}/Lv)", inline=True)
        embed.add_field(name="👟 이동 속도", value=f"`{stats['movespeed']}`", inline=True)

        embed.add_field(name="🛡️ 방어력", value=f"`{stats['armor']}` (+{stats['armorperlevel']}/Lv)", inline=True)
        embed.add_field(name="🔮 마법 저항력", value=f"`{stats['spellblock']}` (+{stats['spellblockperlevel']}/Lv)", inline=True)
        embed.add_field(name="⚔️ 공격력 (AD)", value=f"`{stats['attackdamage']}` (+{stats['attackdamageperlevel']}/Lv)", inline=True)

        embed.add_field(name="💚 체력 재생 (5초)", value=f"`{stats['hpregen']}` (+{stats['hpregenperlevel']}/Lv)", inline=True)
        embed.add_field(name="💙 마나 재생 (5초)", value=f"`{stats['mpregen']}` (+{stats['mpregenperlevel']}/Lv)", inline=True)
        embed.add_field(name="⚡ 공격 속도", value=f"`{stats['attackspeed']}` (+{stats['attackspeedperlevel']}%/Lv)", inline=True)

        passive = champion_data['data'][champion_id]['passive']
        embed.add_field(
            name=f"🟢 패시브 - {passive['name']}",
            value=f"> {passive['description'].replace('<br>', '')}\n",
            inline=False
        )

        spells = champion_data['data'][champion_id]['spells']
        # 3. Q, W, E, R 스킬 정보 반복문으로 추가
        skill_keys = ["Q", "W", "E", "R"]
        for i, spell in enumerate(spells):


            embed.add_field(
                name=f"🔥 {skill_keys[i]} - {spell['name']}",
                value=f"> {spell['description'].replace('<br>', '')}\n"
                    f"⏱️ **쿨타임:** {spell['cooldownBurn'].replace('/', ' / ')}초 |"
                    f"💧 **소모:** {spell['costType'] if spell['costType'] == '소모값 없음' else spell['costBurn']}",
                inline=False
            )

        embed.add_field(name="", value=f"**{'\*'*40}**", inline=False)
    
        # 아군 팁 줄바꿈 처리하여 문자열로 합성
        ally_tips_text = "\n".join([f"- {tip}" for tip in champion_data['data'][champion_id]['allytips']])
        embed.add_field(name="🔵 플레이할 때 (Ally Tips)", value=f"{ally_tips_text}", inline=False)

        # 적군 팁 줄바꿈 처리하여 문자열로 합성
        enemy_tips_text = "\n".join([f"- {tip}" for tip in champion_data['data'][champion_id]['enemytips']])
        embed.add_field(name="🔴 상대할 때 (Enemy Tips)", value=f"{enemy_tips_text}", inline=False)

        embed.set_footer(text=f"lol.ps로 이동  •  Riot Games 제공")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RiotCog(bot))