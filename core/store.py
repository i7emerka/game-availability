"""CSV history of game-launch checks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
CSV_FILE = REPORTS_DIR / "game_checks.csv"

COLUMNS = [
    "datetime",
    "run_id",
    "geo",
    "geo_name",
    "game_id",
    "game_name",
    "section",
    "status",
    "logged_in",
    "deposit_dismissed",
    "load_ms",
    "start_url",
    "final_url",
    "detail",
    "error",
    "screenshot",
]


def load_results() -> pd.DataFrame:
    if not CSV_FILE.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(CSV_FILE)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df


def append_results(rows: list[dict]) -> None:
    if not rows:
        return
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame(rows)
    for col in COLUMNS:
        if col not in new.columns:
            new[col] = ""
    new = new[COLUMNS]
    if CSV_FILE.exists():
        prev = pd.read_csv(CSV_FILE)
        for col in COLUMNS:
            if col not in prev.columns:
                prev[col] = ""
        combined = pd.concat([prev[COLUMNS], new], ignore_index=True)
    else:
        combined = new
    combined.to_csv(CSV_FILE, index=False)
