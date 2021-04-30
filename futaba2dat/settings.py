from pydantic import BaseSettings


class Settings(BaseSettings):
    futaba_catalog_view_cookie: dict = {"cxyl": "100x100x100x1x6"}
    futaba_boards_file: str = "boards.json"
    futaba_board_url: str = "https://{0}.2chan.net/{1}/futaba.php?mode=cat"
    futaba_thread_url: str = "https://{0}.2chan.net/{1}/res/{2}.htm"
    futaba_image_url_root: str = "https://{0}.2chan.net/"

    database_url: str = "sqlite:///futaba2dat_history.db"
