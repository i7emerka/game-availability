"""Site configuration: URL, timeout."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SITE_URL = "https://fastpari.com"
RU_MIRROR_URL = "https://fastpari-5041.pro"


def get_site_url() -> str:
    return (os.getenv("SITE_URL") or DEFAULT_SITE_URL).strip().rstrip("/")


def navigation_timeout_ms() -> int:
    default = 45000
    try:
        env_value = os.getenv("NAVIGATION_TIMEOUT_MS", None)
        if env_value:
            return int(env_value)
    except Exception:
        pass
    return default


def default_game_timeout_s() -> int:
    raw = (os.getenv("GAME_LOAD_TIMEOUT_S") or "70").strip()
    try:
        return max(15, int(raw))
    except ValueError:
        return 70
