import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = str(os.getenv('BOT_TOKEN'))
OPENWEATHERMAP_API = str(os.getenv('OPENWEATHERMAP_API'))
EXCHANGERATE_API = str(os.getenv('EXCHANGERATE_API'))
GENIUS_API = str(os.getenv('GENIUS_API'))
LOSTARK_API = str(os.getenv('LOSTARK_API'))
MAPLESTORY_API = str(os.getenv('MAPLESTORY_API'))
ON_WORD_API = str(os.getenv('ON_WORD_API'))
RIOT_API = str(os.getenv('RIOT_API'))
FIREBASE_CREDENTIALS = str(os.getenv('FIREBASE_CREDENTIALS'))
FIREBASE_URL = str(os.getenv('FIREBASE_URL'))

LOG_FLUSH_INTERVAL = 3600      # 1시간
LOG_MAX_BUFFER_COUNT = 250    # 최대 버퍼 개수
LOG_RETENTION_DAYS = 30        # 보관 기간