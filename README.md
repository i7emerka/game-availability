# Game Availability

Проверка, что **игры Fastpari реально запускаются** с нужного гео.

Не путать с `geo-availability` (там open / redirect / язык / валюта). Здесь сценарий другой:

1. Старт профиля **Dolphin Anty** (RU / BD)
2. Playwright цепляется по CDP
3. Открыть `https://fastpari.com/`, войти в аккаунт гео
4. Открыть игру по прямому пути
5. Закрыть окно пополнения, если вылезло (нулевой баланс — норма)
6. Дождаться **живого стола**, без спина и без ошибки

Семь гео. На каждом одни и те же 5 игр: Crystal, Crash, Burning Hot, Solitaire, Vampire Curse. Дополнительно: Узбекистан 5, Египет 5, Бангладеш 3, Burkina Faso 5, Кот-д’Ивуар 5 (включая Sun of Egypt 3 Hold and Win). Россия и Эфиопия только на общих пяти. Полный прогон — 58 проверок. Пути в `config/games.py`.

Локаль (`/ru`, `/en`, `/bn`) подставляется из URL после логина. Прокси живёт **внутри профиля Dolphin**, в Playwright его нет.

---

## Быстрый старт

Нужен запущенный **Dolphin Anty** с локальным API (`http://127.0.0.1:3001`).

```bash
cd C:\Users\iksau\Desktop\game-availability

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

`playwright install` нужен для драйвера; сам браузер — Dolphin.

Скопируйте env:

```bash
copy .env.example .env
```

Заполните токен Dolphin и логины:

```env
DOLPHIN_API_TOKEN=
DOLPHIN_BASE_URL=http://127.0.0.1:3001

RU_DOLPHIN_PROFILE_ID=825752486
BD_DOLPHIN_PROFILE_ID=822754495

RU_LOGIN=
RU_PASSWORD=
BD_LOGIN=
BD_PASSWORD=
```

Токен тот же, что в `playwrightmonitoring`.

---

## Команды

```bash
# Все гео, у каждого свой список
python check_games.py

# Только Бангладеш: 5 общих и 3 дополнительные
python check_games.py --geos BD

# Одна игра там, где она есть в плане
python check_games.py --games crystal
python check_games.py --geos CI --games sun-of-egypt-3-hold-and-win

# Список конфига
python check_games.py --list

# Без HTML
python check_games.py --no-report

# Проверка + HTML, без публикации
python check_games.py --no-publish
```

После каждой проверки отчёт **автоматически публикуется** на GitHub Pages (если настроен remote).

---

## GitHub Pages

После `python check_games.py` скрипт:

1. Собирает `reports/report.html`
2. Кладёт его в ветку **`gh-pages`** как `index.html` вместе со скринами
3. Пушит на `origin`

### Разовый сетап

1. Создайте **отдельный** репозиторий на GitHub, например `game-availability`
   (не путать с `geo-availability` — там уже свой Pages).

2. Привяжите remote и запушьте код:

```bash
cd C:\Users\iksau\Desktop\game-availability
git remote add origin https://github.com/<user>/game-availability.git
git branch -M main
git push -u origin main
```

3. В GitHub: **Settings → Pages → Build and deployment**
   - Source: **Deploy from a branch**
   - Branch: **`gh-pages`** / **/ (root)** → Save

4. В `.env` (уже по умолчанию):

```env
GITHUB_PAGES_PUBLISH=1
GITHUB_PAGES_BRANCH=gh-pages
GITHUB_PAGES_REMOTE=origin
```

5. Следующий прогон сам обновит сайт:

```bash
python check_games.py
# GitHub Pages: отчёт опубликован — https://<user>.github.io/game-availability/
```

Отключить публикацию: `GITHUB_PAGES_PUBLISH=0` или `--no-publish`.

Коды выхода:

- `0` — нет FAIL
- `1` — ошибка аргументов / конфига
- `2` — есть FAIL

Результаты:

| Файл | Описание |
|------|----------|
| `reports/game_checks.csv` | История |
| `reports/report.html` | Матрица гео × игра + скрины |
| `reports/screenshots/` | Кадр после каждой проверки |

---

## Что считается успехом

**PASS** — после логина игра открылась, стол/слот загрузился (iframe провайдера или canvas), лоадер пропал, на экране нет ошибки региона / maintenance / fail.

**FAIL** — не залогинились, игра не поднялась за таймаут, пустой iframe, явная ошибка провайдера.

Окно «баланс около нуля» **не FAIL**. Спин и ставка не нажимаются. Во время загрузки слота не нажимается Play и не нажимается Escape: Escape уводит в каталог.

---

## Структура

```text
game-availability/
  check_games.py
  config/
    geos.py      # UZ BD RU EG BF CI ET + Dolphin profile_id
    games.py     # пути игр
    site.py
  core/
    dolphin.py
    browser.py
    login.py
    popups.py
    game_launch.py
    runner.py
    store.py
    html_report.py
    publish_report.py
    screenshots.py
  reports/
  .env.example
```
