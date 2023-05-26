from pydantic import BaseSettings


class Settings(BaseSettings):
    futaba_catalog_view_cookie: dict = {"cxyl": "100x100x100x1x6"}
    futaba_boards_file: str = "boards.json"
    futaba_board_url: str = "https://{0}.2chan.net/{1}/futaba.php?mode=cat"
    futaba_thread_url: str = "https://{0}.2chan.net/{1}/res/{2}.htm"
    futaba_image_url_root: str = "https://{0}.2chan.net"
    futaba_bbsmenu_url: str = "https://www.2chan.net/bbsmenu.html"
    futaba_board_uri_pattern: str = r"\/\/(.*?)\.2chan\.net/(.*?)/(futaba|.*enter).htm"

    futaba_uploader_url_small = "http://dec.2chan.net/up2/src/\\1"
    futaba_uploader_url_large = "http://dec.2chan.net/up/src/\\1"
    futaba_uploader_small_re = r"(fu\d+\.(jpg|jpeg|png|gif|mp4|webp|webm))"
    futaba_uploader_large_re = r"(f\d+\.(jpg|jpeg|png|gif|mp4|webp|webm))"

    db_drivername: str = "sqlite"
    db_name: str = "log.sqlite"
    db_user: str = None
    db_pass: str = None
    db_host: str = None
    db_port: str = None
    db_socket_dir: str = "/cloudsql"
    instance_connection_name: str = None
