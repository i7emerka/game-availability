"""BD login smoke test. Credentials come from .env. Same login as check_games.py."""

from config.geos import geo_credentials, get_geo
from config.site import get_site_url, navigation_timeout_ms
from core.browser import connect_to_browser, fresh_page, get_or_create_context
from core.dolphin import cdp_endpoint, start_profile
from core.login import is_logged_in, login_if_needed


def main() -> int:
    geo = get_geo("BD")
    profile_id = int(geo["profile_id"])
    login, password = geo_credentials("BD")
    site = get_site_url()
    print(f"BD profile {profile_id}")
    print(f"Site {site}")

    pw = None
    browser = None
    try:
        automation = start_profile(profile_id)
        endpoint = cdp_endpoint(automation)
        print(f"CDP {endpoint}")
        pw, browser = connect_to_browser(endpoint)
        page = fresh_page(get_or_create_context(browser))
        page.set_default_navigation_timeout(navigation_timeout_ms())
        from core.login import header_text

        try:
            login_if_needed(page, login, password, site_url=site)
        except Exception as exc:
            page.screenshot(path="reports/screenshots/bd_login_fail.jpg")
            print(f"HEADER {header_text(page)}")
            print(f"FAIL {exc}")
            return 1
        ok = is_logged_in(page)
        page.screenshot(path="reports/screenshots/bd_login_ok.jpg")
        print(f"HEADER {header_text(page)}")
        print(f"logged_in={ok} url={page.url}")
        return 0 if ok else 1
    finally:
        # Leave the Dolphin window open. browser.close() would quit it.
        try:
            if pw:
                pw.stop()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
