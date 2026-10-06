"""HTML report: last-run matrix geo × game + history."""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

from config.games import GAMES, games_for_geo
from config.geos import list_geo_codes
from core.store import CSV_FILE, load_results

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
HTML_FILE = REPORTS_DIR / "report.html"
HISTORY_ROWS_PER_PAGE = 20


def _esc(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return html.escape(str(val), quote=True)


def _status_class(status: str) -> str:
    s = (status or "").upper()
    if s == "PASS":
        return "pass"
    if s == "SKIP":
        return "skip"
    return "fail"


def _status_badge(status: str) -> str:
    s = (status or "—").upper()
    return f'<span class="status status-{_status_class(s)}">{_esc(s)}</span>'


def _ms(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)) or str(val).strip() == "":
        return "—"
    try:
        return f"{int(float(val))} ms"
    except (TypeError, ValueError):
        return _esc(val)


def _shot(path_val, caption: str) -> str:
    raw = "" if path_val is None or (isinstance(path_val, float) and pd.isna(path_val)) else str(path_val).strip()
    if not raw or raw.lower() in {"nan", "none"}:
        return ""
    rel = raw.replace("\\", "/")
    if rel.startswith("reports/"):
        rel = rel[len("reports/") :]
    if not rel.startswith("screenshots/"):
        rel = "screenshots/" + rel.lstrip("/")
    return (
        f'<a class="shot" href="{_esc(rel)}" target="_blank" rel="noopener">'
        f'<img src="{_esc(rel)}" alt="{_esc(caption)}" />'
        f"<span>{_esc(caption)}</span></a>"
    )


def _latest_run(df: pd.DataFrame) -> pd.DataFrame:
    """Latest CSV row per geo × game, so a RU-only rerun does not hide the rest."""
    if df.empty:
        return df
    work = df.copy()
    work["_ord"] = range(len(work))
    work["geo"] = work["geo"].astype(str)
    work["game_id"] = work["game_id"].astype(str)
    work = work.sort_values("_ord").drop_duplicates(subset=["geo", "game_id"], keep="last")
    planned = []
    for geo in work["geo"].unique():
        allowed = {item["id"] for item in games_for_geo(geo)}
        planned.append(work[(work["geo"] == geo) & (work["game_id"].isin(allowed))])
    work = pd.concat(planned, ignore_index=True) if planned else work.iloc[0:0]
    return work.drop(columns=["_ord"]).reset_index(drop=True)


def _matrix(last: pd.DataFrame) -> str:
    if last.empty:
        return "<p class='muted'>Пока нет прогонов.</p>"

    geos = list(list_geo_codes())
    extra = [g for g in last["geo"].astype(str).unique() if g not in geos]
    geos.extend(extra)
    games = list(GAMES)

    head = "".join(
        f"<th>{_esc(g['name'])}<div class='cell-sub'>{_esc(g.get('section') or '')}</div></th>"
        for g in games
    )
    body_rows = []
    for geo in geos:
        name = ""
        cells = [f"<th class='geo-cell'><span class='geo-code'>{_esc(geo)}</span></th>"]
        for game in games:
            planned = {item["id"] for item in games_for_geo(geo)}
            chunk = last[(last["geo"].astype(str) == geo) & (last["game_id"].astype(str) == game["id"])]
            if chunk.empty:
                if game["id"] not in planned:
                    cells.append("<td class='center muted' title='не в плане'>·</td>")
                else:
                    cells.append("<td class='center muted'>—</td>")
                continue
            r = chunk.iloc[-1]
            name = str(r.get("geo_name") or "")
            st = str(r.get("status") or "")
            shot = _shot(r.get("screenshot"), game["id"])
            err = str(r.get("error") or r.get("detail") or "")
            cells.append(
                f"<td class='cell-{_status_class(st)}'>"
                f"<div class='cell-top'>{_status_badge(st)}"
                f"<span class='ms'>{_ms(r.get('load_ms'))}</span></div>"
                f"{shot}"
                f"<div class='cell-sub' title='{_esc(err)}'>{_esc(err[:80])}</div>"
                f"</td>"
            )
        if name:
            cells[0] = (
                f"<th class='geo-cell'><span class='geo-code'>{_esc(geo)}</span>"
                f"<div class='cell-sub'>{_esc(name)}</div></th>"
            )
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    return f"""
    <div class="panel table-wrap">
      <table class="matrix">
        <thead><tr><th>Гео</th>{head}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </div>
    """


def _history(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    view = df.iloc[::-1]
    rows = []
    for index, (_, r) in enumerate(view.iterrows(), start=1):
        st = str(r.get("status") or "")
        rows.append(
            f"<tr class='data-row row-{_status_class(st)}'>"
            f"<td class='row-num'>{index}</td>"
            f"<td class='time-main'>{_esc(r.get('datetime'))}</td>"
            f"<td><span class='geo-code'>{_esc(r.get('geo'))}</span></td>"
            f"<td>{_esc(r.get('game_name'))}<div class='cell-sub'>{_esc(r.get('section'))}</div></td>"
            f"<td>{_status_badge(st)}</td>"
            f"<td>{_ms(r.get('load_ms'))}</td>"
            f"<td class='url'>{_esc(r.get('final_url'))}</td>"
            f"<td>{_shot(r.get('screenshot'), 'shot')}</td>"
            f"</tr>"
        )
    total = len(rows)
    return f"""
    <section>
      <h2>История</h2>
      <div class="panel">
        <div class="table-wrap">
          <table class="report-table">
            <thead>
              <tr>
                <th class="col-num">#</th>
                <th>Время</th><th>Гео</th><th>Игра</th><th>Статус</th>
                <th>Загрузка</th><th>URL</th><th>Скрин</th>
              </tr>
            </thead>
            <tbody id="report-body">{''.join(rows)}</tbody>
          </table>
        </div>
        <div class="pagination" id="table-pagination" data-rows-per-page="{HISTORY_ROWS_PER_PAGE}" data-total-rows="{total}">
          <button type="button" class="page-btn" id="page-prev" disabled>← Назад</button>
          <span class="page-info" id="page-info"></span>
          <button type="button" class="page-btn" id="page-next">Вперёд →</button>
        </div>
      </div>
    </section>
    """


def generate_html_report() -> Path:
    df = load_results()
    last = _latest_run(df)
    ts = ""
    if not last.empty and "datetime" in last.columns:
        ts = str(last["datetime"].iloc[-1])

    statuses = last["status"].astype(str).str.upper() if not last.empty and "status" in last.columns else pd.Series(dtype=str)
    total = len(last)
    passes = int((statuses == "PASS").sum())
    fails = int((statuses == "FAIL").sum())
    rate = f"{(passes / total * 100):.0f}%" if total else "—"

    html_doc = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Game Availability</title>
  <style>
    :root {{
      --bg0: #f7f9fd; --bg1: #e8eef8;
      --card: #ffffff;
      --card-border: #d5deee;
      --text: #1d2b44; --muted: #5d6d86;
      --line: #e3eaf4;
      --pass: #148a5e; --pass-bg: #e5f7ee;
      --fail: #c53d4a; --fail-bg: #fdecee;
      --skip: #6b778c; --skip-bg: #eef1f5;
      --accent: #3b7ddd;
      --thead: #f3f6fb;
      --shadow: 0 10px 28px rgba(40, 64, 110, 0.08);
      --radius: 16px;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      min-height: 100vh;
      font-family: "Segoe UI", ui-sans-serif, system-ui, Roboto, Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(1100px 520px at 8% -12%, rgba(90, 150, 255, 0.16), transparent 55%),
        linear-gradient(180deg, var(--bg0), var(--bg1) 48%, #dfe7f4);
    }}
    .page {{ max-width: 1280px; margin: 0 auto; padding: 28px 28px 48px; }}
    h1 {{ margin: 0; font-size: 1.6rem; letter-spacing: -0.02em; }}
    h2 {{ margin: 28px 0 12px; font-size: 1.1rem; }}
    .subtitle {{ margin-top: 6px; color: var(--muted); }}
    .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }}
    .kpi {{
      background: var(--card); border: 1px solid var(--card-border);
      border-radius: 14px; padding: 14px 16px; box-shadow: var(--shadow);
    }}
    .kpi-label {{ color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; }}
    .kpi-value {{ font-size: 1.5rem; font-weight: 700; margin-top: 4px; }}
    .kpi-pass .kpi-value {{ color: var(--pass); }}
    .kpi-fail .kpi-value {{ color: var(--fail); }}
    .kpi-rate .kpi-value {{ color: var(--accent); }}
    .panel {{
      background: var(--card); border: 1px solid var(--card-border);
      border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden;
    }}
    .table-wrap {{ overflow: auto; }}
    table {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.875rem; }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    thead th {{
      text-align: left; font-size: 0.72rem; letter-spacing: 0.05em; text-transform: uppercase;
      color: var(--muted); background: var(--thead); position: sticky; top: 0;
    }}
    .geo-code {{
      display: inline-flex; min-width: 42px; justify-content: center;
      padding: 4px 10px; border-radius: 8px; font-weight: 700; font-size: 0.8rem;
      color: #265a9c; background: #e8f1fc; border: 1px solid #c5daf5;
    }}
    .status {{
      display: inline-flex; padding: 4px 10px; border-radius: 999px;
      font-size: 0.72rem; font-weight: 800; letter-spacing: 0.04em;
    }}
    .status-pass {{ color: var(--pass); background: var(--pass-bg); }}
    .status-fail {{ color: var(--fail); background: var(--fail-bg); }}
    .status-skip {{ color: var(--skip); background: var(--skip-bg); }}
    .cell-pass {{ box-shadow: inset 3px 0 0 var(--pass); }}
    .cell-fail {{ box-shadow: inset 3px 0 0 var(--fail); }}
    .row-pass {{ box-shadow: inset 3px 0 0 var(--pass); }}
    .row-fail {{ box-shadow: inset 3px 0 0 var(--fail); }}
    .cell-top {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }}
    .ms {{ color: var(--muted); font-variant-numeric: tabular-nums; font-size: 0.8rem; }}
    .cell-sub {{ margin-top: 4px; color: var(--muted); font-size: 0.75rem; max-width: 280px;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .muted {{ color: var(--muted); }}
    .center {{ text-align: center; }}
    .url {{ max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--muted); }}
    .time-main {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
    .shot {{ display: inline-flex; flex-direction: column; gap: 4px; color: var(--muted); font-size: 0.7rem; text-decoration: none; }}
    .shot img {{ width: 160px; height: 90px; object-fit: cover; border-radius: 8px; border: 1px solid var(--line); background: #f3f6fb; }}
    .matrix .shot img {{ width: 180px; height: 102px; }}
    .col-num, .row-num {{
      width: 44px; text-align: right; color: var(--muted);
      font-variant-numeric: tabular-nums; font-weight: 700;
    }}
    .pagination {{
      display: flex; align-items: center; justify-content: center;
      gap: 16px; padding: 12px 16px 16px;
    }}
    .page-btn {{
      border: 1px solid var(--card-border); background: #fff; color: var(--text);
      border-radius: 8px; padding: 8px 14px; font-size: 0.85rem; cursor: pointer;
    }}
    .page-btn:hover:not(:disabled) {{ border-color: var(--accent); color: var(--accent); }}
    .page-btn:disabled {{ opacity: 0.45; cursor: not-allowed; }}
    .page-info {{ color: var(--muted); font-size: 0.85rem; min-width: 220px; text-align: center; }}
    .hidden-row {{ display: none !important; }}
  </style>
</head>
<body>
  <div class="page">
    <header>
      <h1>Game Availability</h1>
      <div class="subtitle">Fastpari · актуальный статус по гео × игра · {_esc(ts)}</div>
    </header>
    <div class="kpis">
      <div class="kpi"><div class="kpi-label">Проверок</div><div class="kpi-value">{total}</div></div>
      <div class="kpi kpi-pass"><div class="kpi-label">PASS</div><div class="kpi-value">{passes}</div></div>
      <div class="kpi kpi-fail"><div class="kpi-label">FAIL</div><div class="kpi-value">{fails}</div></div>
      <div class="kpi kpi-rate"><div class="kpi-label">Успех</div><div class="kpi-value">{rate}</div></div>
    </div>
    <h2>Последний прогон</h2>
    {_matrix(last)}
    {_history(df)}
  </div>
  <script>
    (function initTablePagination() {{
      const pagination = document.getElementById('table-pagination');
      const prevBtn = document.getElementById('page-prev');
      const nextBtn = document.getElementById('page-next');
      const pageInfo = document.getElementById('page-info');
      const rows = Array.from(document.querySelectorAll('#report-body tr.data-row'));
      if (!pagination || rows.length === 0) {{
        if (pagination) pagination.style.display = 'none';
        return;
      }}
      const rowsPerPage = Number(pagination.dataset.rowsPerPage || 20);
      const totalPages = Math.max(1, Math.ceil(rows.length / rowsPerPage));
      let currentPage = 1;
      function renderPage() {{
        rows.forEach((row, index) => {{
          const page = Math.floor(index / rowsPerPage) + 1;
          row.classList.toggle('hidden-row', page !== currentPage);
        }});
        pageInfo.textContent = 'Страница ' + currentPage + ' из ' + totalPages + ' · записей: ' + rows.length;
        prevBtn.disabled = currentPage <= 1;
        nextBtn.disabled = currentPage >= totalPages;
      }}
      prevBtn.addEventListener('click', () => {{
        if (currentPage > 1) {{ currentPage -= 1; renderPage(); }}
      }});
      nextBtn.addEventListener('click', () => {{
        if (currentPage < totalPages) {{ currentPage += 1; renderPage(); }}
      }});
      if (totalPages <= 1) pagination.style.display = 'none';
      renderPage();
    }})();
  </script>
</body>
</html>
"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    HTML_FILE.write_text(html_doc, encoding="utf-8")
    return HTML_FILE
