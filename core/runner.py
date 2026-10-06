"""Run  geo × game checks through Dolphin + Playwright."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config.geos import geo_credentials, get_geo
from config.site import get_site_url, navigation_timeout_ms
from core.browser import connect_to_browser, disconnect, fresh_page, get_or_create_context
from core.dolphin import cdp_endpoint, start_profile, stop_profile
from core.game_launch import launch_game
from core.login import is_logged_in, login_if_needed
from core.screenshots import capture_safe, prune_screenshots, screenshot_path


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _empty_row(
    geo_code: str,
    geo: dict,
    game: dict,
    run_id: str,
    *,
    status: str = "FAIL",
    error: str = "",
) -> dict[str, Any]:
    return {
        "datetime": _now(),
        "run_id": run_id,
        "geo": geo_code,
        "geo_name": geo["name"],
        "game_id": game["id"],
        "game_name": game["name"],
        "section": game["section"],
        "status": status,
        "logged_in": False,
        "deposit_dismissed": False,
        "load_ms": None,
        "start_url": game.get("path") or "",
        "final_url": "",
        "detail": "",
        "error": error,
        "screenshot": "",
    }


def check_geo(
    geo_code: str,
    games: list[dict],
    *,
    run_id: str,
    keep_open: bool = False,
) -> list[dict[str, Any]]:
    geo = get_geo(geo_code)
    profile_id = geo.get("profile_id")
    login, password = geo_credentials(geo_code)
    site = get_site_url()
    nav_timeout = navigation_timeout_ms()

    print(f"\n=== {geo_code} {geo['name']}  Dolphin {profile_id} ===")

    pw = None
    browser = None
    page = None
    logged_in = False
    results: list[dict[str, Any]] = []

    try:
        if not profile_id:
            raise RuntimeError(
                f"{geo_code}: в .env нет {geo.get('profile_env') or 'Dolphin profile id'}"
            )
        automation = start_profile(int(profile_id))
        endpoint = cdp_endpoint(automation)
        print(f"  CDP {endpoint}")
        pw, browser = connect_to_browser(endpoint)
        context = get_or_create_context(browser)
        page = fresh_page(context)
        # Добавляем обработку SSL-ошибок
        if not hasattr(context, '_ssl_handled'):
            context._ssl_handled = True
        page.set_default_timeout(15000)
        page.set_default_navigation_timeout(nav_timeout)

        login_if_needed(page, login, password, site_url=site, geo_code=geo_code)
        logged_in = True

        for game in games:
            print(f"  {game['section']} / {game['name']}")
            if not is_logged_in(page):
                print("  account missing, logging in again")
                login_if_needed(page, login, password, site_url=site, geo_code=geo_code)
            row = _empty_row(geo_code, geo, game, run_id)
            row["logged_in"] = True
            launched = None
            for attempt in (1, 2):
                try:
                    launched = launch_game(page, game)
                except Exception as exc:
                    launched = {
                        "ok": False,
                        "url": game.get("path") or "",
                        "final_url": page.url if page else "",
                        "load_ms": None,
                        "deposit_dismissed": False,
                        "detail": str(exc),
                    }
                if launched.get("ok") or attempt == 2:
                    break
                print(f"  {game['name']} did not open, retry")
            row["start_url"] = launched.get("url") or game["path"]
            row["final_url"] = launched.get("final_url") or ""
            row["load_ms"] = launched.get("load_ms")
            row["deposit_dismissed"] = bool(launched.get("deposit_dismissed"))
            row["detail"] = launched.get("detail") or ""
            row["status"] = "PASS" if launched.get("ok") else "FAIL"
            if not launched.get("ok"):
                row["error"] = launched.get("detail") or "game did not load"

            # Frame is already up. The table inside needs longer.
            shot_wait_s = 60 if game.get("section") == "slots" else 45
            print(f"  wait {shot_wait_s}s before screenshot")
            if page:
                page.wait_for_timeout(shot_wait_s * 1000)
            dest = screenshot_path(run_id, geo_code, game["id"])
            row["screenshot"] = capture_safe(page, dest)
            print(f"    {row['status']}  {row['error'] or row['detail']}")
            results.append(row)

        return results
    except Exception as exc:
        err = str(exc)
        print(f"  geo failed: {err}")
        if results:
            # Remaining games not attempted.
            done_ids = {r["game_id"] for r in results}
            pending = [g for g in games if g["id"] not in done_ids]
        else:
            pending = games
        for game in pending:
            row = _empty_row(geo_code, geo, game, run_id, error=err)
            row["logged_in"] = logged_in
            if page:
                dest = screenshot_path(run_id, geo_code, game["id"])
                row["screenshot"] = capture_safe(page, dest)
                row["final_url"] = page.url
            results.append(row)
        return results
    finally:
        if keep_open:
            # Drop Playwright only. browser.close() would quit the Dolphin window.
            try:
                if pw:
                    pw.stop()
            except Exception:
                pass
        else:
            disconnect(pw, browser)
            if profile_id:
                stop_profile(int(profile_id))
        prune_screenshots()


def check_many(
    geo_codes: list[str],
    games: list[dict],
    *,
    run_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for code in geo_codes:
        rows.extend(check_geo(code, games, run_id=run_id))
    return rows
