"""Games to launch after login.

Five titles run on every geo. Uzbekistan, Egypt, Bangladesh, Burkina Faso,
and Cote d'Ivoire also get their own extra titles. Russia and Ethiopia stay
on the shared five.
"""

from __future__ import annotations


def _entry(path: str, name: str, section: str, timeout_s: int) -> dict:
    return {
        "id": path.rstrip("/").split("/")[-1],
        "name": name,
        "section": section,
        "path": path,
        "load_timeout_s": timeout_s,
    }


def _games(path: str, name: str) -> dict:
    return _entry(path, name, "games", 50)


def _slot(path: str, name: str) -> dict:
    return _entry(path, name, "slots", 70)


def _index(entries: list[dict]) -> dict[str, dict]:
    return {entry["id"]: entry for entry in entries}


_COMMON = [
    _games("/games/crystal", "Crystal"),
    _games("/games/crash", "Crash"),
    _games("/games/burning-hot", "Burning Hot"),
    _games("/games/solitaire", "Solitaire"),
    _games("/games/vampire-curse", "Vampire Curse"),
]

_EXTRAS: dict[str, list[dict]] = {
    "UZ": [
        _slot(
            "/slots/game/136651/gates-of-olympus-super-scatter",
            "Gates of Olympus Super Scatter",
        ),
        _games("/games/western-slot", "Western Slot"),
        _games("/games/gems-odyssey", "Gems Odyssey"),
        _slot("/slots/game/95426/sweet-bonanza-1000", "Sweet Bonanza 1000"),
        _slot("/slots/game/179195/mummyland-treasures", "Mummyland Treasures"),
    ],
    "EG": [
        _slot("/slots/game/89896/sugar-rush-1000", "Sugar Rush 1000"),
        _games("/games/apple-of-fortune", "Apple of Fortune"),
        _games("/games/midgard-zombies", "Midgard Zombies"),
        _games("/games/las-vegas", "Las Vegas"),
        _games("/games/under-and-over-seven", "Under and Over Seven"),
    ],
    "BD": [
        _slot("/slots/game/78711/queen-halloween", "Queen Halloween"),
        _games("/games/scratch-card", "Scratch Card"),
        _slot("/slots/game/75282/wild-bandito", "Wild Bandito"),
    ],
    "BF": [
        _games("/games/twenty-one", "Twenty One"),
        _slot("/slots/game/85785/zeus-vs-hades-gods-of-war", "Zeus vs Hades: Gods of War"),
        _slot("/slots/game/69056/gates-of-olympus", "Gates of Olympus"),
        _slot("/slots/game/162016/fortune-of-olympus", "Fortune of Olympus"),
        _games("/games/mayan-tomb", "Mayan Tomb"),
    ],
    "CI": [
        _slot("/slots/game/85837/gates-of-olympus-1000", "Gates of Olympus 1000"),
        _slot("/slots/game/155629/egypt-fire-2", "Egypt Fire 2"),
        _slot("/slots/game/67766/sun-of-egypt-3-hold-and-win", "Sun of Egypt 3 Hold and Win"),
        _slot("/slots/game/135447/pirate-queen-2", "Pirate Queen 2"),
        _slot("/slots/game/69212/big-bass-splash", "Big Bass Splash"),
    ],
}

_BY_ID = _index(_COMMON)
for _extra in _EXTRAS.values():
    _BY_ID.update(_index(_extra))

# Stable catalog: shared five, then each geo's extras in plan order.
GAMES: list[dict] = list(_COMMON)
for _code in ("UZ", "EG", "BD", "BF", "CI"):
    GAMES.extend(_EXTRAS[_code])


def list_game_ids() -> list[str]:
    return [game["id"] for game in GAMES]


def games_for_geo(code: str) -> list[dict]:
    """Shared five, then that geo's extras. Russia and Ethiopia have no extras."""
    key = (code or "").strip().upper()
    return [dict(game) for game in (*_COMMON, *_EXTRAS.get(key, []))]


def get_games(ids: list[str] | None = None) -> list[dict]:
    if not ids:
        return list(GAMES)
    wanted = {item.strip().lower() for item in ids if item.strip()}
    found = [game for game in GAMES if game["id"] in wanted]
    unknown = wanted - {game["id"] for game in found}
    if unknown:
        raise KeyError(
            f"Unknown games: {', '.join(sorted(unknown))}. Known: {', '.join(list_game_ids())}"
        )
    return found
