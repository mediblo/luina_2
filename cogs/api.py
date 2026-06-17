import discord
from discord.ext import commands
from discord import app_commands

from config.settings import openweathermap_api, exchangerate_api
from utils.embed_builder import build_simple_embed
from utils.http_client import get_json

class ApiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="날씨", description="해당 지역에 대한 날씨 정보를 알려줍니다 ( 한국, 시 한정 )") # 날씨 201206 / 211228 / 230621 / 260617
    @app_commands.describe(city="지역 이름 (서울)")
    async def weather(self, interaction: discord.interactions, city:str):
        api_url = f'http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=5&appid={openweathermap_api}' # 동일 이름 최대 5개 서치 (Direct geocoding )
        api_data = await get_json(api_url)
        location = {}
        for x in api_data:
            if x['country'] == 'KR':
                api_url = f'https://api.openweathermap.org/data/2.5/weather?lat={x['lat']}&lon={x['lon']}&appid={openweathermap_api}' # 날씨 정보 ( current weather data )
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
                
        api_url=f'https://v6.exchangerate-api.com/v6/{exchangerate_api}/latest/{country}'
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

async def setup(bot):
    await bot.add_cog(ApiCog(bot))