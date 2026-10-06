"""JPEG screenshots for each game check."""

from __future__ import annotations

import base64
from pathlib import Path

from playwright.sync_api import Page

from core.store import REPORTS_DIR

SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
KEEP_FILES = 80


def screenshot_path(run_id: str, geo: str, game_id: str) -> Path:
    slug = "".join(ch if ch.isalnum() else "_" for ch in (run_id or ""))
    slug = slug.strip("_")[:32] or "run"
    game = "".join(ch if ch.isalnum() else "_" for ch in (game_id or "game"))[:40]
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    return SCREENSHOTS_DIR / f"{slug}_{geo}_{game}.jpg"


def relative_shot_url(path: Path) -> str:
    return f"screenshots/{path.name}"


def _write_jpeg(dest: Path, data: bytes) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    if dest.stat().st_size <= 0:
        raise OSError(f"empty screenshot {dest.name}")
    return relative_shot_url(dest)


def capture_safe(page: Page | None, dest: Path) -> str:
    """Save a JPEG even when the page is still loading fonts.

    page.screenshot() waits for web fonts and times out on slot frames.
    Chrome's captureScreenshot does not, so that path is used first.
    """
    if page is None:
        return ""
    try:
        if page.is_closed():
            print(f"  screenshot fail ({dest.name}): page is closed")
            return ""
    except Exception:
        return ""

    try:
        client = page.context.new_cdp_session(page)
        try:
            result = client.send(
                "Page.captureScreenshot",
                {"format": "jpeg", "quality": 70},
            )
        finally:
            try:
                client.detach()
            except Exception:
                pass
        return _write_jpeg(dest, base64.b64decode(result["data"]))
    except Exception as exc:
        print(f"  screenshot via browser failed ({dest.name}): {exc}")

    try:
        page.screenshot(
            path=str(dest),
            type="jpeg",
            quality=70,
            full_page=False,
            timeout=8000,
            animations="disabled",
        )
        if dest.exists() and dest.stat().st_size > 0:
            return relative_shot_url(dest)
    except Exception as exc:
        print(f"  screenshot fail ({dest.name}): {exc}")
    return ""


def prune_screenshots(keep: int = KEEP_FILES) -> None:
    if not SCREENSHOTS_DIR.exists():
        return
    files = sorted(
        [
            p
            for p in SCREENSHOTS_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for stale in files[keep:]:
        try:
            stale.unlink()
        except OSError:
            pass
