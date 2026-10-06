"""Dismiss cookies, bonus splash, and zero-balance deposit modals."""

from __future__ import annotations

import re

from playwright.sync_api import Page

CLOSE_SELECTORS = (
    "button[aria-label='Close' i]",
    "button[aria-label='Закрыть']",
    "[class*='modal'] button[class*='close' i]",
    "[class*='popup'] button[class*='close' i]",
    "[class*='dialog'] button[class*='close' i]",
    "[class*='overlay'] button[class*='close' i]",
    "button.close",
    ".modal-close",
    ".popup-close",
    "[data-testid='close']",
    "[class*='icon-close']",
    "button:has(svg[class*='close' i])",
)

CLOSE_NAME = re.compile(
    r"^(×|✕|✖|x|close|закрыть|no thanks|maybe later|later|skip|not now|cancel|отмена)$",
    re.I,
)

ACCEPT_NAME = re.compile(
    r"accept( all)?|agree|allow|принять|согласен|хорошо|ok,?\s*got it",
    re.I,
)

# Do not click deposit / play CTAs when closing a wallet prompt.
AVOID_CLICK = re.compile(
    r"deposit|пополн|recharge|add funds|wallet|pay|купить|play|играть|spin|demo",
    re.I,
)


def _safe_click(locator, *, timeout: int = 800) -> bool:
    try:
        if locator.count() == 0:
            return False
        target = locator.first
        if not target.is_visible(timeout=timeout):
            return False
        text = (target.inner_text(timeout=timeout) or "").strip()
        if text and AVOID_CLICK.search(text) and not CLOSE_NAME.search(text):
            return False
        target.click(timeout=timeout)
        return True
    except Exception:
        return False


def dismiss_cookies(page: Page) -> bool:
    clicked = False
    for pattern in (ACCEPT_NAME,):
        loc = page.get_by_role("button", name=pattern)
        if _safe_click(loc, timeout=600):
            clicked = True
            break
    return clicked


def _click_close_controls(page: Page) -> bool:
    clicked = False
    for selector in CLOSE_SELECTORS:
        try:
            loc = page.locator(selector)
            if _safe_click(loc, timeout=400):
                clicked = True
        except Exception:
            continue
    loc = page.get_by_role("button", name=CLOSE_NAME)
    if _safe_click(loc, timeout=400):
        clicked = True
    return clicked


def dismiss_overlay(page: Page) -> bool:
    """Close whatever modal is on top: X, Escape, overlay, corner click."""
    closed = _click_close_controls(page)
    try:
        page.keyboard.press("Escape")
        closed = True
    except Exception:
        pass

    overlay = page.locator(
        ".modal-overlay, .overlay, [class*='backdrop'], [class*='modal-mask']"
    ).first
    try:
        if overlay.count() and overlay.is_visible(timeout=300):
            box = overlay.bounding_box()
            if box and box["width"] > 50 and box["height"] > 50:
                page.mouse.click(box["x"] + 16, box["y"] + 16)
                closed = True
    except Exception:
        pass

    if not closed:
        try:
            page.mouse.click(24, 24)
            closed = True
        except Exception:
            pass
    return closed


def dismiss_site_popups(page: Page, *, rounds: int = 4) -> None:
    """Lobby / after-login splash: cookies, bonus, age, wallet nag."""
    for _ in range(rounds):
        did = False
        did = dismiss_cookies(page) or did
        did = _click_close_controls(page) or did
        if not did:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            break
        page.wait_for_timeout(400)


ZERO_BALANCE = re.compile(
    r"your balance is near zero|balance is near zero|баланс близок к нулю",
    re.I,
)


def dismiss_deposit_modal(page: Page) -> bool:
    """Close only the zero-balance dialog. Escape leaves a slot and opens the catalog."""
    hint = page.get_by_text(ZERO_BALANCE)
    try:
        if hint.count() == 0 or not hint.first.is_visible(timeout=400):
            return False
    except Exception:
        return False

    dialog = page.locator("[role='dialog'], [class*='modal'], [class*='popup']").filter(
        has_text=ZERO_BALANCE
    )
    close = dialog.locator(
        "button[aria-label='Close' i], button[aria-label='Закрыть'], button[class*='close' i]"
    )
    if _safe_click(close, timeout=800):
        return True
    return _safe_click(dialog.get_by_role("button", name=CLOSE_NAME), timeout=800)
