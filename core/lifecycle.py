import asyncio

from services import shutdown as log_shutdown


async def graceful_shutdown(bot):
    """
    프로그램 종료 처리
    """

    await log_shutdown()

    await bot.close()