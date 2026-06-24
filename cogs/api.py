import discord
from discord.ext import commands
from discord import app_commands
import lyricsgenius
from typing import Optional

from config.settings import OPENWEATHERMAP_API, EXCHANGERATE_API, ON_WORD_API, GENIUS_API
from utils.embed_builder import build_simple_embed
from utils.http_client import get_json, get_response

class ApiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.riot_emoji = await self.bot.fetch_application_emojis() # 이모지 불러오기
        api_url = [
            f'https://kli.korean.go.kr/term/api/search.do?key={ON_WORD_API}', # 온 용어
            f'https://api.openweathermap.org/data/2.5/weather?q=Seoul&appid={OPENWEATHERMAP_API}', # 오픈웨더맵
            f'https://v6.exchangerate-api.com/v6/{EXCHANGERATE_API}/latest/USD', # Exchangerate
        ]
        api_name = [
            '온 용어', '오픈웨더맵', 'Exchangerate',
        ]

        for i in range(len(api_url)):
            api_data = await get_response(api_url[i])
            status = api_data.status_code
            if 200 <= status < 300:
                print(f"🟢 {api_name[i]} | Status: {status} (정상 연결)")
            
            # 🟡 노랑 동그라미: 호출 제한 초과 (429) 또는 일시적 서버 에러 (500대)
            elif status == 429 or status >= 500:
                print(f"🟡 {api_name[i]} | Status: {status} (호출 제한 또는 서버 지연)")
            
            # 🔴 빨강 동그라미: 인증 실패 (401, 403) 및 기타 잘못된 요청 (400대)
            else:
                print(f"🔴 {api_name[i]} | Status: {status} (인증 실패 또는 잘못된 요청)")

    @app_commands.command(name="날씨", description="해당 지역에 대한 날씨 정보를 알려줍니다 ( 한국, 시 한정 )") # 날씨 201206 / 211228 / 230621 / 260617
    @app_commands.describe(city="지역 이름 (서울)")
    async def weather(self, interaction: discord.interactions, city:str):
        api_url = f'http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=5&appid={OPENWEATHERMAP_API}' # 동일 이름 최대 5개 서치 (Direct geocoding )
        api_data = await get_json(api_url)
        location = {}
        for x in api_data:
            if x['country'] == 'KR':
                api_url = f"https://api.openweathermap.org/data/2.5/weather?lat={x['lat']}&lon={x['lon']}&appid={OPENWEATHERMAP_API}" # 날씨 정보 ( current weather data )
                weather_data = await get_json(api_url)

                location['city'] = f"{city}" # 지역
                location['lat'] = x['lat'] # 위도
                location['lon'] = x['lon'] # 경도
                location['temp'] = weather_data['main']['temp'] - 273.15 # 현재 온도
                location['temp_min'] = weather_data['main']['temp_min'] - 273.15 # 최저 온도
                location['temp_max'] = weather_data['main']['temp_max'] - 273.15 # 최고 온도
                location['feel'] = weather_data['main']['feels_like'] - 273.15 # 체감 온도
                location['humidity'] = weather_data['main']['humidity'] # 습도
                location['weather'] = weather_data['weather'][0]['main'] # 날씨
                location['icon'] = weather_data['weather'][0]['icon'] # icon id
                location['rain'] = weather_data.get('rain', {}).get('1h', 0) # 시간당 강수량
                location['clouds'] = weather_data['clouds']['all'] # 구름 량
                location['wind_speed'] = weather_data['wind']['speed'] # 풍속

                break

        if not location:
            await interaction.response.send_message("지역을 찾지 못했어요!", ephemeral=True)
            return

        embed=build_simple_embed(
            title=f"📍 {location['city']} 날씨 정보",
            description=f"현재 상태: **{location['weather']}** (구름량 {location['clouds']}%)",
        )

        icon_url = f"https://openweathermap.org/img/wn/{location['icon']}@2x.png"
        embed.set_thumbnail(url=icon_url)
        embed.add_field(name="🌡️ 현재 기온", value=f"{location['temp']:.2f}°C", inline=True)
        embed.add_field(name="🤔 체감 온도", value=f"{location['feel']:.2f}°C", inline=True)
        embed.add_field(name="📊 최저 / 최고", value=f"{location['temp_min']:.2f}°C / {location['temp_max']:.2f}°C", inline=True)

        # 환경 정보
        embed.add_field(name="💦 습도", value=f"{location['humidity']}%", inline=True)
        embed.add_field(name="💨 풍속", value=f"{location['wind_speed']} m/s", inline=True)
        embed.add_field(name="🌧️ 강수량 (1시간)", value=f"{location['rain']} mm", inline=True)

        # 하단 푸터 (좌표 및 출처 표시)
        embed.set_footer(text=f"위도: {location['lat']} | 경도: {location['lon']}     •     OpenWeatherMap 제공")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

#########################################################################################################

    @app_commands.command(name="환율", description="환율을 알려줍니다! 기본 [ 한국 | 1000원 ]") # 환율 221025 / 260617
    @app_commands.choices(
        country=[
            app_commands.Choice(name="🇰🇷 대한민국 원", value="KRW",),
            app_commands.Choice(name="🇨🇳 중국 위안", value="CNY"),
            app_commands.Choice(name="🇯🇵 일본 엔", value="JPY"),
            app_commands.Choice(name="🇺🇸 미국 달러", value="USD"),
            app_commands.Choice(name="🇮🇩 인도 루피", value="INR"),
            app_commands.Choice(name="🇪🇺 유럽 유로", value="EUR"),
            app_commands.Choice(name="🇬🇧 영국 파운드", value="GBP"),
            app_commands.Choice(name="🇷🇺 러시아 루블", value="RUB"),
            app_commands.Choice(name="🇵🇭 필리핀 페소", value="PHP"),
        ] 
    )
    @app_commands.describe(price ="가격 입력")
    async def weather(self, interaction: discord.interactions, country: str= 'KRW', price: int= 1000):
        COUNTRY_MAP = {
            "KRW": "🇰🇷 대한민국 원 (KRW)",
            "CNY": "🇨🇳 중국 위안 (CNY)",
            "JPY": "🇯🇵 일본 엔 (JPY)",
            "USD": "🇺🇸 미국 달러 (USD)",
            "INR": "🇮🇳 인도 루피 (INR)",
            "EUR": "🇪🇺 유럽 유로 (EUR)",
            "GBP": "🇬🇧 영국 파운드 (GBP)",
            "RUB": "🇷🇺 러시아 루블 (RUB)",
            "PHP": "🇵🇭 필리핀 페소 (PHP)",
        }

        EXCHANGE_RATES = {
            "KRW": 1.0, "USD": 1350.0, "JPY": 9.0, "EUR": 1450.0,
            "CNY": 185.0, "GBP": 1700.0, "INR": 16.0, "RUB": 15.0, "PHP": 24.0
        }
                
        api_url=f'https://v6.exchangerate-api.com/v6/{EXCHANGERATE_API}/latest/{country}'
        api_data = await get_json(api_url)

        for cty in COUNTRY_MAP.keys():
            EXCHANGE_RATES[cty] = api_data["conversion_rates"][cty] * price

        embed = build_simple_embed(
            title="💱 실시간 환율 정보",
            description=f"환율 정보입니다.",
        )
        for key, value in EXCHANGE_RATES.items():
            embed.add_field(name=COUNTRY_MAP[key], value=f"{value:.2f}")

        embed.set_footer(text=f"UTC 기준 {api_data['time_last_update_utc']}     •     Exchangerate 제공")
        await interaction.response.send_message(embed=embed, ephemeral=True)

#########################################################################################################

    @app_commands.command(name="사전", description="단어에 대한 사전적 용어를 알려줍니다") # 사전 201105 / 260618
    @app_commands.describe(word="단어 입력")
    async def word_dictonary(self, interaction: discord.interactions, word:str):
        api_url=f'https://kli.korean.go.kr/term/api/search.do?key={ON_WORD_API}&apiSearchWord={word}&sort=wt&start=1&num=5'
        api_data = await get_json(api_url)

        if api_data['channel'].get('returnCode') == "1":
            await interaction.response.send_message(api_data['channel']['return_object'], ephemeral=True)
            return

        word_data = {}

        data = api_data['channel']['return_object'][0]['resultlist'][0]
        word_data['word'] = data['word']
        word_data['description'] = data['definition']
        word_data['category'] = f"{data['category_main']} > {data['category_sub']}"
        word_data['origin'] = f"{data['origin_cc']}"
        word_data['use_ex'] = data["use_ex"].replace("<strong>", "**").replace("</strong>", "**")
        word_data['source'] = f"{data['glossary']} {data['source']}"

        embed = build_simple_embed(
            title="사전",
            description="📚  국립국어원 정보"
        )

        embed.add_field(
            name=f"📖 {word_data['word']} {word_data['origin']}",
            value = word_data['description'],
            inline=False
        )

        # 4. 필드 추가 (분류 및 출처)
        embed.add_field(
            name="📂 분류",
            value=word_data['category'],
            inline=True,
        )
        embed.add_field(
            name="📍 출처",
            value=word_data['source'],
            inline=True,
        )

        if data['use_ex']:
            embed.add_field(name="📝 예문", value=word_data['use_ex'], inline=False)

        embed.set_footer(text=f"{api_data['channel']['title']} 제공")

        # 메시지 전송
        await interaction.response.send_message(embed=embed, ephemeral = True)

#########################################################################################################

    @app_commands.command(name="가사", description="노래에 대한 가사를 알려줍니다.") # 가사 201203 / 260623
    @app_commands.describe(song="노래 제목")
    @app_commands.describe(artist="가수 (선택사항)")
    async def search_lyric(self, interaction: discord.interactions, song:str, artist:Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        genius = lyricsgenius.Genius(GENIUS_API, skip_non_songs=True)
        
        data = genius.search_song(song, artist=artist)
        
        if not data:
            await interaction.followup.send(
                f"❌ **'{song}'** (아티스트: {artist or '미지정'})에 대한 가사를 찾을 수 없습니다.", 
                ephemeral=True
            )
            return

        # 1. 기본 임베드 디자인 세팅
        embed = build_simple_embed(
            title=data.title,
            description=f"**아티스트:** {data.artist}"
        )
        embed.url = data.url

        if data.song_art_image_url:
            embed.set_thumbnail(url=data.song_art_image_url)

        # 2. 🔥 가사 데이터 정제 (중요!)
        lyrics = data.lyrics

        # [텍스트 가사] 형식으로 시작하는 첫 번째 줄(찌꺼기) 제거
        lines = lyrics.split("\n")
        if lines and lines[0].startswith("[") and "가사" in lines[0]:
            lines = lines[1:]  # 첫 줄을 버립니다.
        lyrics = "\n".join(lines).strip()

        # Genius 특유의 맨 끝 "숫자Embed" 찌꺼기 제거 (예: "25Embed" -> 제거)
        if lyrics.endswith("Embed"):
            lyrics = lyrics[:-5]  # 끝의 "Embed" 글자 제거
            # 그 직전에 남은 숫자들도 제거
            while lyrics and lyrics[-1].isdigit():
                lyrics = lyrics[:-1]
            lyrics = lyrics.strip()

        # 3. 디스코드 글자 수 한계(필드당 900자)에 맞춰 이쁘게 쪼개기
        max_length = 900
        
        if len(lyrics) <= max_length:
            embed.add_field(name="🎤 가사", value=f"```txt\n{lyrics}\n```", inline=False)
            await interaction.followup.send(embed=embed, ephemeral = True)
        else:
            # 가사가 길면 900자 단위로 쪼갬
            lyrics_chunks = [lyrics[i:i+max_length] for i in range(0, len(lyrics), max_length)]
            
            # 첫 번째 파트는 원래 interaction 응답으로 전송
            embed.add_field(name="🎤 가사 (1/n)", value=f"```txt\n{lyrics_chunks[0]}\n```", inline=False)
            await interaction.followup.send(embed=embed, ephemeral = True)
            
            # 두 번째 파트부터는 followup 기능을 이용해 순차적으로 전송
            for idx, chunk in enumerate(lyrics_chunks[1:], start=2):
                next_embed = discord.Embed(color=0xFFEB3B)
                next_embed.add_field(
                    name=f"🎤 가사 이어보기 ({idx}/{len(lyrics_chunks)})", 
                    value=f"```txt\n{chunk}\n```", 
                    inline=False
                )
                await interaction.followup.send(embed=next_embed, ephemeral = True)

#########################################################################################################

async def setup(bot):
    await bot.add_cog(ApiCog(bot))