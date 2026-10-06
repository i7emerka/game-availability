# Модули для импорта через from core import games, site, runner

from config.games import GAMES as _GAMES


class games:
    """Games configuration module. The list lives in config/games.py."""
    GAMES_CONFIG = _GAMES

    @staticmethod
    def list_game_ids():
        from config.games import list_game_ids as _list
        return _list()

    @staticmethod
    def get_games(ids=None):
        from config.games import get_games as _get
        return _get(ids)

    @staticmethod
    def games_for_geo(code):
        from config.games import games_for_geo as _for_geo
        return _for_geo(code)


SITE_URL = "http://fastpari.com"

class site:
    """Site configuration module."""
    SITE_URL = SITE_URL
    
    @staticmethod
    def get_site_url():
        from config.site import get_site_url as _get
        return _get()
    
    @staticmethod
    def navigation_timeout_ms():
        from config.site import navigation_timeout_ms as _nav
        return _nav()


# Импорты runner для функций — исправленный импорт generate_html_report из html_report.py
from core.runner import check_geo, check_many
from core.html_report import generate_html_report as _generate_html_report

runner = type('runner', (), {
    'check_geo': check_geo,
    'check_many': check_many,
    'generate_html_report': _generate_html_report,
})

__all__ = ['games', 'site', 'runner']
