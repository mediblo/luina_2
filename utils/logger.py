import logging
import sys

logger = logging.getLogger("discord_bot")

# 이미 Handler가 등록되어 있으면 중복 등록 방지
if not logger.handlers:
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

# 상위 Logger로 전달 방지
logger.propagate = False

def _build_message(message: str, source: str, user: str | None = None) -> str:
    if user:
        return f"[{source}] [{user}] {message}"
    return f"[{source}] {message}"


def log_info(message: str, source: str = "System", user: str | None = None):
    logger.info(_build_message(message, source, user))


def log_warning(message: str, source: str = "System", user: str | None = None):
    logger.warning(_build_message(message, source, user))


def log_error(message: str, source: str = "System", user: str |None = None):
    logger.error(_build_message(message, source, user))


def log_exception(message: str, source: str = "System", user: str | None = None): # Only Exception
    logger.exception(_build_message(message, source, user))