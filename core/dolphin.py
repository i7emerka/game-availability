"""Dolphin Anty local API: start/stop profiles for Playwright CDP."""

from __future__ import annotations

import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = (os.getenv("DOLPHIN_BASE_URL") or "http://127.0.0.1:3001").rstrip("/")
API_TOKEN = (os.getenv("DOLPHIN_API_TOKEN") or "").strip()


class DolphinError(RuntimeError):
    pass


def _check_token() -> None:
    if not API_TOKEN:
        raise DolphinError("DOLPHIN_API_TOKEN is not set in .env")


def authorize() -> dict:
    _check_token()
    response = requests.post(
        f"{BASE_URL}/v1.0/auth/login-with-token",
        headers={"Content-Type": "application/json"},
        json={"token": API_TOKEN},
        timeout=30,
    )
    try:
        data = response.json()
    except ValueError as exc:
        raise DolphinError(
            f"Dolphin auth: HTTP {response.status_code}, not JSON: {response.text[:300]}"
        ) from exc
    if not response.ok or not data.get("success"):
        hint = ""
        if response.status_code == 401:
            hint = (
                " Token expired or invalid — in Dolphin Anty open API, "
                "copy a new token into DOLPHIN_API_TOKEN."
            )
        raise DolphinError(
            f"Dolphin auth failed HTTP {response.status_code}: {data}.{hint}"
        )
    return data


def _automation_from_devtools(profile_id: int) -> dict | None:
    """Port file Dolphin writes for a profile that is already open."""
    path = (
        Path(os.environ.get("APPDATA", ""))
        / "dolphin_anty"
        / "browser_profiles"
        / str(profile_id)
        / "data_dir"
        / "DevToolsActivePort"
    )
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or not lines[0].strip().isdigit():
        return None
    ws = lines[1].strip() if len(lines) > 1 else ""
    return {"port": int(lines[0].strip()), "wsEndpoint": ws}


def _read_start(profile_id: int) -> tuple[requests.Response, dict]:
    response = requests.get(
        f"{BASE_URL}/v1.0/browser_profiles/{profile_id}/start",
        params={"automation": 1},
        timeout=60,
    )
    try:
        data = response.json()
    except ValueError:
        data = {}
    return response, data


def start_profile(profile_id: int, *, restart: bool = False) -> dict:
    """Start the profile, or attach if it is already open. Does not close it."""
    authorize()
    if restart:
        stop_profile(profile_id)

    response, data = _read_start(profile_id)
    message = str(data.get("error") or data.get("message") or "")
    if "already running" in message.lower():
        # Dolphin sometimes returns the port only on the next call.
        for _ in range(5):
            time.sleep(1)
            response, data = _read_start(profile_id)
            if data.get("success") and data.get("automation"):
                break
        else:
            found = _automation_from_devtools(profile_id)
            if found:
                return found

    if response.status_code == 500 and "already running" in message.lower():
        found = _automation_from_devtools(profile_id)
        if found:
            return found

    if not response.ok or not data.get("success"):
        msg = message or "unknown error"
        if "payment is required" in msg.lower() or response.status_code == 402:
            raise DolphinError(
                f"Dolphin start {profile_id}: payment required (HTTP 402). "
                "Starter plan expired — renew the Dolphin subscription, then retry."
            )
        found = _automation_from_devtools(profile_id)
        if found and "already running" in msg.lower():
            return found
        raise DolphinError(f"Dolphin start {profile_id} failed: {msg}")
    automation = data.get("automation") or {}
    if not automation:
        raise DolphinError(f"Dolphin start {profile_id}: no automation endpoint in {data}")
    return automation


def stop_profile(profile_id: int) -> None:
    try:
        authorize()
        requests.get(
            f"{BASE_URL}/v1.0/browser_profiles/{profile_id}/stop",
            timeout=30,
        )
    except Exception:
        pass


def cdp_endpoint(automation: dict) -> str:
    """HTTP CDP URL for Playwright connect_over_cdp (not the ws:// DevTools path)."""
    port = automation.get("port")
    if port:
        return f"http://127.0.0.1:{port}"

    ws = (automation.get("wsEndpoint") or automation.get("ws") or "").strip()
    if ws:
        # ws://127.0.0.1:9222/devtools/browser/<id> → http://127.0.0.1:9222
        from urllib.parse import urlparse

        parsed = urlparse(ws if "://" in ws else f"http://{ws}")
        if parsed.hostname and parsed.port:
            return f"http://{parsed.hostname}:{parsed.port}"
        if parsed.hostname:
            return f"http://{parsed.hostname}:9222"
    raise DolphinError(f"Dolphin automation has no port/wsEndpoint: {automation}")
