"""Playwright connected to a running Dolphin profile via CDP."""

from __future__ import annotations

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


def connect_to_browser(cdp_url: str):
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp(cdp_url)
    except Exception:
        try:
            pw.stop()
        except Exception:
            pass
        raise
    return pw, browser


def get_or_create_context(browser: Browser) -> BrowserContext:
    if browser.contexts:
        # Используем существующий контекст
        context = browser.contexts[0]
    else:
        # Создаём новый контекст с настройками для игнорирования SSL-ошибок
        context = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1920, "height": 1080},
        )
    
    return context


def get_page(context: BrowserContext) -> Page:
    pages = [p for p in context.pages if not p.is_closed()]
    if pages:
        page = pages[-1]
        try:
            page.bring_to_front()
        except Exception:
            pass
        return page
    return context.new_page()


def fresh_page(context: BrowserContext) -> Page:
    """Close every tab Dolphin restored, then work in a new one.

    The new tab is opened first. Closing the last tab would quit the window.
    """
    page = context.new_page()
    closed = 0
    for old in list(context.pages):
        if old is page or old.is_closed():
            continue
        try:
            old.close()
            closed += 1
        except Exception:
            pass
    try:
        page.bring_to_front()
    except Exception:
        pass
    print(f"  closed {closed} old tab(s), opened a new one")
    return page


def disconnect(pw, browser) -> None:
    try:
        if browser:
            browser.close()
    except Exception:
        pass
    try:
        if pw:
            pw.stop()
    except Exception:
        pass
