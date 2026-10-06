"""Geo profiles: Dolphin id + Fastpari account."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

def _profile_id(env_key: str, default: str = "") -> int | None:
    raw = (os.getenv(env_key) or default).strip()
    if not raw:
        return None
    return int(raw)


def _geo(name: str, profile_env: str, default_profile: str = "") -> dict:
    return {
        "name": name,
        "profile_env": profile_env,
        "profile_id": _profile_id(profile_env, default_profile),
        "login_env": profile_env.split("_DOLPHIN")[0] + "_LOGIN",
        "password_env": profile_env.split("_DOLPHIN")[0] + "_PASSWORD",
    }


GEOS: dict[str, dict] = {
    "UZ": _geo("Uzbekistan", "UZ_DOLPHIN_PROFILE_ID"),
    "BD": _geo("Bangladesh", "BD_DOLPHIN_PROFILE_ID", "822754495"),
    "RU": _geo("Russia", "RU_DOLPHIN_PROFILE_ID", "825752486"),
    "EG": _geo("Egypt", "EG_DOLPHIN_PROFILE_ID"),
    "BF": _geo("Burkina Faso", "BF_DOLPHIN_PROFILE_ID"),
    "CI": _geo("Cote d'Ivoire", "CI_DOLPHIN_PROFILE_ID"),
    "ET": _geo("Ethiopia", "ET_DOLPHIN_PROFILE_ID"),
}


def list_geo_codes() -> list[str]:
    return list(GEOS.keys())


def get_geo(code: str) -> dict:
    key = code.strip().upper()
    if key not in GEOS:
        raise KeyError(f"Unknown geo: {code}. Known: {', '.join(GEOS)}")
    return GEOS[key]


def geo_credentials(code: str) -> tuple[str, str]:
    geo = get_geo(code)
    login = (os.getenv(geo["login_env"]) or "").strip()
    password = (os.getenv(geo["password_env"]) or "").strip()
    if not login or not password:
        raise RuntimeError(
            f"{code}: missing {geo['login_env']} / {geo['password_env']} in .env"
        )
    return login, password
