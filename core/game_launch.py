"""Open a game URL and wait until the live table/slot is up, with no error."""

from __future__ import annotations

import re
import time
from urllib.parse import urljoin, urlparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config.site import default_game_timeout_s

ERROR_RE = re.compile(
    r"not available|unavailable|not available in (your )?(country|region)|"
    r"isn'?t available|cannot be (played|opened)|geo.?block|"
    r"maintenance|something went wrong|game error|failed to load|"
    r"cannot launch|access denied|session expired|try again later|"
    r"blocked in your|is not supported|provider error|"
    r"игра недоступн|недоступна в|техническ(ие|ая) работ",
    re.I,
)

INSPECT_JS = r"""() => {
  const visible = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    return r.width > 40 && r.height > 40
      && st.visibility !== 'hidden'
      && st.display !== 'none'
      && st.opacity !== '0';
  };

  const text = (document.body && document.body.innerText || '').slice(0, 12000);
  const iframes = [...document.querySelectorAll('iframe')].filter(visible);
  const canvases = [...document.querySelectorAll('canvas')].filter(visible);
  const loaders = [...document.querySelectorAll(
    ".loader, .spinner, .preloader, [class*='loading'], [class*='spinner'], [class*='preloader']"
  )].filter(visible);

  const skipSrc = /recaptcha|gtm|googletag|facebook|hotjar|doubleclick|sentry|cookie|suphelper|support|jivo|intercom|chatwoot|livechat/i;
  const gameIframes = iframes.filter(f => {
    const src = f.getAttribute('src') || f.src || '';
    const r = f.getBoundingClientRect();
    return r.width >= 240 && r.height >= 180 && !skipSrc.test(src);
  });

  return {
    text,
    iframeCount: gameIframes.length,
    iframeSrc: gameIframes.map(f => f.src || f.getAttribute('src') || '').slice(0, 4),
    canvasCount: canvases.length,
    loaderVisible: loaders.length > 0,
  };
}"""


def locale_prefix(url: str) -> str:
    path = urlparse(url).path or ""
    parts = [p for p in path.split("/") if p]
    if not parts:
        return ""
    seg = parts[0]
    if len(seg) == 2 and seg.isalpha():
        return "/" + seg.lower()
    if len(seg) == 5 and seg[2] == "-" and seg[:2].isalpha() and seg[3:].isalpha():
        return "/" + seg.lower()
    return ""


def origin_of(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def is_slots_catalog(url: str) -> bool:
    """True for /slots, false for /slots/game/..."""
    path = (urlparse(url).path or "").rstrip("/").lower()
    return path.endswith("/slots")


def game_url(page_url: str, game_path: str) -> str:
    origin = origin_of(page_url)
    prefix = locale_prefix(page_url)
    path = game_path if game_path.startswith("/") else "/" + game_path
    if prefix and not path.startswith(prefix + "/") and path != prefix:
        path = prefix + path
    return urljoin(origin + "/", path.lstrip("/"))


def _error_from_text(text: str) -> str:
    if not text:
        return ""
    match = ERROR_RE.search(text)
    if not match:
        return ""
    # Tiny snippet around the hit so the report is readable.
    start = max(0, match.start() - 40)
    end = min(len(text), match.end() + 40)
    snippet = re.sub(r"\s+", " ", text[start:end]).strip()
    return snippet or match.group(0)


def inspect(page: Page) -> dict:
    try:
        data = page.evaluate(INSPECT_JS)
    except Exception as exc:
        return {
            "text": "",
            "iframeCount": 0,
            "iframeSrc": [],
            "canvasCount": 0,
            "loaderVisible": False,
            "error": f"inspect failed: {exc}",
        }
    data = data or {}
    text = data.get("text") or ""
    data["error"] = _error_from_text(text)
    if re.search(r"\b0\s*%", text):
        data["loaderVisible"] = True
    return data


DEMO_SRC = re.compile(r"demogamesfree|/demo\?|plustrial|plus.?trial", re.I)


def _demo_srcs(info: dict) -> list[str]:
    return [src for src in (info.get("iframeSrc") or []) if DEMO_SRC.search(src or "")]


def _looks_loaded(info: dict) -> bool:
    if info.get("error"):
        return False
    if info.get("loaderVisible"):
        return False
    if _demo_srcs(info) and not any(
        src for src in (info.get("iframeSrc") or []) if src and not DEMO_SRC.search(src)
    ):
        return False
    iframes = int(info.get("iframeCount") or 0)
    canvases = int(info.get("canvasCount") or 0)
    return iframes > 0 or canvases > 0


def wait_for_game(page: Page, *, timeout_s: int) -> tuple[bool, str, dict]:
    """
    Returns (ok, detail, last_inspect).
    No clicks while the game opens. A guest demo frame is not a loaded game.
    """
    deadline = time.time() + timeout_s
    stable = 0
    last: dict = {}

    try:
        while time.time() < deadline:
            last = inspect(page)
            if last.get("error"):
                return False, f"game error: {last['error']}", last
            if _looks_loaded(last):
                stable += 1
                if stable >= 2:
                    src = ", ".join(last.get("iframeSrc") or []) or "canvas"
                    return True, f"loaded ({src})", last
            else:
                stable = 0
            page.wait_for_timeout(1000)
    except PlaywrightTimeoutError:
        pass

    if _demo_srcs(last):
        return False, "opened as a guest demo, account session is gone", last
    bits = []
    if last.get("loaderVisible"):
        bits.append("loader still visible")
    bits.append(f"iframes={last.get('iframeCount', 0)}")
    bits.append(f"canvas={last.get('canvasCount', 0)}")
    return False, "timeout waiting for game: " + ", ".join(bits), last


def launch_game(page: Page, game: dict) -> dict:
    timeout_s = int(game.get("load_timeout_s") or default_game_timeout_s())
    url = game_url(page.url, game["path"])
    started = time.time()
    detail = ""
    deposit = False

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
    except PlaywrightTimeoutError:
        # Game shell may keep connections open; continue and inspect anyway.
        detail = "navigation timeout, inspecting anyway"
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "final_url": page.url,
            "load_ms": int((time.time() - started) * 1000),
            "deposit_dismissed": False,
            "detail": f"navigation failed: {exc}",
        }

    page.wait_for_timeout(500)
    if "/slots/game/" in url and is_slots_catalog(page.url):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
            page.wait_for_timeout(500)
        except PlaywrightTimeoutError:
            detail = "navigation timeout, inspecting anyway"
        except Exception as exc:
            detail = f"navigation failed: {exc}"

    ok, wait_detail, _info = wait_for_game(page, timeout_s=timeout_s)
    if "/slots/game/" in url and is_slots_catalog(page.url):
        ok = False
        wait_detail = "site opened the slots list instead of the game"
    if detail:
        wait_detail = f"{detail}; {wait_detail}"
    return {
        "ok": ok,
        "url": url,
        "final_url": page.url,
        "load_ms": int((time.time() - started) * 1000),
        "deposit_dismissed": deposit,
        "detail": wait_detail,
    }
