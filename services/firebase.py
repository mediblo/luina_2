from config.settings import FIREBASE_CREDENTIALS, FIREBASE_URL
from utils.logger import logger

from firebase_admin import credentials
from firebase_admin import db
import firebase_admin
import json
from datetime import timedelta, timezone
import datetime

cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS))
firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})

is_connected = db.reference('connected').get()
if is_connected:
    logger.info("🟢 Firebase (정상연결)")
else:
    logger.info("🔴 Firebase (연결 끊어짐)")


async def save_logs(day: str, hour:str, logs: list[str]):
    db.reference(f'logs/{day}/{hour}').set(logs)
    logger.info(f"로그 {len(logs)}개 저장", "Firebase")

async def delete_old_logs():
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)
    days_later = now - timedelta(days=30)
    days_later = days_later.strftime("%Y-%m-%d")

    db.reference(f"logs/{days_later}").delete()
    logger.info(f"{days_later} 로그 삭제", "Firebase")