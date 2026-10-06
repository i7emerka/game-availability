"""Fastpari login via the dedicated /user/login page.

Opens /en/user/login and waits up to 60 seconds for the form to appear.
Then waits 5 seconds, fills login and password, submits, and waits 25 seconds.
If the account header is still missing, the same login is tried once more.
For Russia, a dead fastpari.com falls back to https://fastpari-5041.pro/ru.
Games are not opened until that header is visible.
"""

from __future__ import annotations

import re
import time
from urllib.parse import urlparse

from playwright.sync_api import Page

from config.site import RU_MIRROR_URL

PRIMARY_LOGIN = "https://fastpari.com/en/user/login"
RU_MIRROR_HOME = f"{RU_MIRROR_URL}/ru"
RU_MIRROR_LOGIN = f"{RU_MIRROR_URL}/ru/user/login"

EMAIL_RE = re.compile(r"e-?mail or id|e-?mail или id", re.I)
PASSWORD_RE = re.compile(r"password|пароль", re.I)
LOGIN_BTN_RE = re.compile(r"^(log in|войти)$", re.I)


def english_home(site_url: str) -> str:
    raw = (site_url or "").strip()
    if raw and "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError(f"Bad site url: {site_url}")
    return f"{parsed.scheme}://{parsed.netloc}/en"


def _visible(locator, timeout: int = 800) -> bool:
    try:
        return locator.count() > 0 and locator.first.is_visible(timeout=timeout)
    except Exception:
        return False


def header_text(page: Page) -> str:
    try:
        raw = page.locator("header").inner_text(timeout=1000) or ""
    except Exception:
        return ""
    return " ".join(raw.split())


def header_is_guest(page: Page) -> bool:
    text = header_text(page)
    if not text:
        return False
    return bool(
        re.search(
            r"registration|регистрац|sign up|\blog in\b|\blogin\b|\bвход\b|\bвойти\b",
            text,
            re.I,
        )
    )


ACCOUNT_RE = re.compile(
    r"main account|личный кабинет|основн(ой|ый)(\s+сч[её]т)?",
    re.I,
)


def is_logged_in(page: Page) -> bool:
    """True when the account label is visible anywhere, not only inside <header>."""
    label = page.get_by_text(ACCOUNT_RE)
    if _visible(label, 1500):
        return True
    text = header_text(page)
    if text and ACCOUNT_RE.search(text) and not header_is_guest(page):
        return True
    try:
        body = page.locator("body").inner_text(timeout=2000) or ""
    except Exception:
        return False
    return bool(ACCOUNT_RE.search(body))


def login_page_url(site_url: str) -> str:
    """Default English login on the main site."""
    return PRIMARY_LOGIN


def _is_dead_page(page: Page) -> bool:
    url = (page.url or "").lower()
    return url.startswith("chrome-error:") or "chromewebdata" in url


def _email_box(page: Page):
    return page.get_by_role("textbox", name=EMAIL_RE)


def _open_url(page: Page, url: str) -> None:
    print(f"  open {url}")
    try:
        # domcontentloaded only. "load" on this casino often never fires through a proxy.
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as exc:
        print(f"  page still loading ({type(exc).__name__})")
        if _is_dead_page(page):
            raise RuntimeError(f"site did not open ({page.url})") from exc
        return
    if _is_dead_page(page):
        raise RuntimeError(f"site did not open ({page.url})")


def _wait_login_form(page: Page) -> str:
    """Wait until the form is shown, or the account is already on screen.

    A second visit to /user/login often redirects home when the first
    attempt already created the session. That is a success, not a missing form.
    """
    print("  wait for login form")
    field = _email_box(page)
    deadline = time.time() + 60
    while time.time() < deadline:
        if _is_dead_page(page):
            raise RuntimeError(f"site did not open ({page.url})")
        if is_logged_in(page):
            return "session"
        if _visible(field, 500):
            return "form"
        page.wait_for_timeout(1000)
    if is_logged_in(page):
        return "session"
    raise RuntimeError(f"Login form did not appear (url={page.url})")


def _submit_login(page: Page, login: str, password: str, url: str) -> None:
    _open_url(page, url)
    if is_logged_in(page):
        print("  already logged in")
        return
    if _wait_login_form(page) == "session":
        print("  already logged in")
        return
    print("  wait 5s")
    page.wait_for_timeout(5000)
    print("  logging in...")
    _email_box(page).fill(login, timeout=20000)
    page.get_by_role("textbox", name=PASSWORD_RE).fill(password, timeout=20000)
    page.locator("form").get_by_role("button", name=LOGIN_BTN_RE).click(timeout=20000)
    print("  wait 25s")
    page.wait_for_timeout(25000)


def _try_login_url(
    page: Page,
    login: str,
    password: str,
    url: str,
    *,
    attempts: int = 2,
) -> Exception | None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        print(f"  login attempt {attempt} ({url})")
        try:
            _submit_login(page, login, password, url)
        except Exception as exc:
            if is_logged_in(page):
                print("  logged in")
                return None
            last_error = exc
            print(f"  login attempt {attempt} failed: {exc}")
            if _is_dead_page(page):
                return last_error
            continue
        if is_logged_in(page):
            print("  logged in")
            return None
        last_error = RuntimeError(f"session was not created (url={page.url})")
        print(f"  login attempt {attempt}: account is not on the page")
    return last_error


def _login_url_from_page(page: Page) -> str:
    try:
        raw = page.url or ""
    except Exception:
        return ""
    if not raw or _is_dead_page(page):
        return ""
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""
    parts = [p for p in (parsed.path or "").split("/") if p]
    prefix = "en"
    if parts and len(parts[0]) == 2 and parts[0].isalpha():
        prefix = parts[0].lower()
    return f"{parsed.scheme}://{parsed.netloc}/{prefix}/user/login"


def login_if_needed(
    page: Page,
    login: str,
    password: str,
    *,
    site_url: str | None = None,
    geo_code: str | None = None,
) -> None:
    """Log in twice at most on the main site. Russia then tries the 5041 mirror."""
    geo = (geo_code or "").strip().upper()
    last_error: Exception | None = None

    current = _login_url_from_page(page)
    if current and current != PRIMARY_LOGIN:
        last_error = _try_login_url(page, login, password, current)
        if last_error is None:
            return

    last_error = _try_login_url(page, login, password, PRIMARY_LOGIN)
    if last_error is None:
        return

    if geo == "RU":
        print(f"  RU did not open on fastpari.com, trying {RU_MIRROR_HOME}")
        try:
            _open_url(page, RU_MIRROR_HOME)
        except Exception as exc:
            last_error = exc
            print(f"  RU mirror home failed: {exc}")
        else:
            if is_logged_in(page):
                print("  logged in")
                return
        last_error = _try_login_url(page, login, password, RU_MIRROR_LOGIN)
        if last_error is None:
            return

    raise RuntimeError(f"Login failed after 2 attempts: {last_error}")
