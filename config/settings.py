import os

BOT_TOKEN = "Nzk0MTEyNDYxNzQxMzU5MTI0.GX35Uy.h25plJGRpZBVDiQqF_GCH2afBG1scscCaKApqM" # 봇 토큰
TEST_GUILD_ID = 736512667530821653 # 테스트 서버 ID


riot_Api=str(os.getenv('riot_api')) # 롤 API
win_api=str(os.getenv('win_api')) # 윈섭 API
client_id = str(os.getenv('naver_cli_id')) # 네이버 클라 id
client_secret = str(os.getenv('naver_cli_secret')) # 네이버 클라 시크릿
weather_api = str(os.getenv('openweather_api')) # openweather map API
exchangerate_api = str(os.getenv('exchange_api')) # excgangerate API
korea_api = str(os.getenv('korea_api')) # 공공데이터포탈 api
lostark_api = str(os.getenv('lostark_api')) # 로스트아크 api

headers = {
    'accept' : 'application/json',
    'authorization' : lostark_api
}

## TODO : api 작동 확인 코드