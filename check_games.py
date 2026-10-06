import argparse
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from config.site import get_site_url
from core import games, runner
from core.publish_report import publish_report
from core.store import append_results


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-report', action='store_true', help="Don't generate a report")
    parser.add_argument(
        '--no-publish',
        action='store_true',
        help="Do not publish report to GitHub Pages",
    )
    parser.add_argument(
        '--geos',
        type=str,
        default=None,
        help="Comma-separated geo codes (UZ,BD,RU,EG,BF,CI,ET)",
    )
    parser.add_argument('--games', type=str, default=None, help="Comma-separated game names to test")
    parser.add_argument('--list', action='store_true', help="List available games/geos")
    args = parser.parse_args()

    # List mode
    if args.list:
        from config.geos import list_geo_codes

        print("\n=== Games by geo ===")
        for code in list_geo_codes():
            planned = games.games_for_geo(code)
            print(f"\n  {code}: {len(planned)}")
            for game in planned:
                print(f"    {game['id']}: {game['name']} ({game['section']})")

        print("\n=== Available Geos ===")
        from config import geos
        for code in list_geo_codes():
            geo = geos.get_geo(code)
            profile = geo["profile_id"] or "нет в .env"
            print(f"\n  {code}: {geo['name']}")
            print(f"    Profile ID: {profile}")

        return 0

    from config.games import get_games
    from config.geos import list_geo_codes

    selected_ids = None
    if args.games:
        selected_ids = {game["id"] for game in get_games(args.games.split(","))}

    geo_codes = list_geo_codes()
    if args.geos:
        geo_codes = [code.strip().upper() for code in args.geos.split(",")]

    # Generate run ID
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    print(f"Site URL: {get_site_url()}")
    print("Starting game availability checks...")

    rows = []
    for code in geo_codes:
        planned = games.games_for_geo(code)
        if selected_ids is not None:
            planned = [game for game in planned if game["id"] in selected_ids]
        if not planned:
            print(f"{code}: в плане нет выбранных игр")
            continue
        print(f"{code}: {len(planned)} игр")
        rows.extend(runner.check_geo(code, planned, run_id=run_id))

    # Print summary
    total = len(rows)
    passed = sum(1 for r in rows if r['status'] == 'PASS')
    failed = sum(1 for r in rows if r['status'] == 'FAIL')

    print(f"\n=== Summary ===")
    print(f"Total checks: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    # Print failures
    if failed > 0:
        print("\n=== Failed Checks ===")
        for r in rows:
            if r['status'] == 'FAIL':
                print(f"\n{r['datetime']} | {r['geo']} | {r['game_name']}")
                print(f"  Error: {r['error']}")

    append_results(rows)

    # Generate HTML report (unless disabled)
    if not args.no_report:
        path = runner.generate_html_report()
        print(f"\nHTML Report saved to: {path}")
        if not args.no_publish and _env_bool("GITHUB_PAGES_PUBLISH", True):
            publish_report(path)

    return 2 if failed > 0 else 0


if __name__ == "__main__":
    exit(main())
