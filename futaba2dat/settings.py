from pydantic import BaseSettings


class Settings(BaseSettings):
    futaba_catalog_view_cookie: dict = {"cxyl": "100x100x100x1x6"}
    futaba_boards_file: str = "boards.json"
    futaba_board_url: str = "https://{0}.2chan.net/{1}/futaba.php?mode=cat"
    futaba_thread_url: str = "https://{0}.2chan.net/{1}/res/{2}.htm"
    futaba_image_url_root: str = "https://{0}.2chan.net/"
    futaba_bbsmenu_url: str = "https://www.2chan.net/bbsmenu.html"
    futaba_board_uri_pattern: str = r"\/\/(.*?)\.2chan\.net/(.*?)/(futaba|.*enter).htm"

    database_url: str = "sqlite:///log.sqlite"
