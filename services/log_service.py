from collections import defaultdict
from datetime import datetime
import asyncio

from config.settings import LOG_FLUSH_INTERVAL, LOG_MAX_BUFFER_COUNT

from utils.logger import log_exception

from services.firebase import (
    save_logs,
    delete_old_logs
)

# day -> hour -> list[str]
_buffer = defaultdict(lambda: defaultdict(list))
_buffer_count = 0

_flush_lock = asyncio.Lock()


def append(log: str):
    global _buffer_count

    now = datetime.now()

    day = now.strftime("%Y-%m-%d")
    hour = now.strftime("%H")

    _buffer[day][hour].append(log)
    _buffer_count += 1

    if _buffer_count >= LOG_MAX_BUFFER_COUNT:
        asyncio.create_task(flush())


async def flush_task():
    while True:
        await asyncio.sleep(LOG_FLUSH_INTERVAL)
        await flush()


async def flush():
    """
    메모리 버퍼 → Firebase
    """
    global _buffer
    global _buffer_count

    async with _flush_lock:

        if _buffer_count == 0:
            return

        logs = _buffer

        _buffer = defaultdict(lambda: defaultdict(list))
        _buffer_count = 0

    try:
        for day, hours in logs.items():
            for hour, log_list in hours.items():
                await save_logs(
                    day=day,
                    hour=hour,
                    logs=log_list
                )

    except Exception:

        # 저장 실패 시 로그 복구
        async with _flush_lock:

            for day, hours in logs.items():
                for hour, log_list in hours.items():
                    _buffer[day][hour].extend(log_list)
                    _buffer_count += len(log_list)

        log_exception(
            "Firebase 로그 저장 실패",
            source="Logger"
        )


async def startup():
    """
    봇 시작 시 실행
    """
    await delete_old_logs()


async def shutdown():
    """
    종료 직전 실행
    """
    await flush()