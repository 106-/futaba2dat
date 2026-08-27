from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Settings:
    upstream_timeout_ms: int = 15_000
    upstream_max_response_bytes: int = 8 * 1024 * 1024
    futaba_catalog_view_cookie: dict[str, str] = field(
        default_factory=lambda: {"cxyl": "100x100x100x1x6"}
    )
    futaba_board_url: str = "https://{0}.2chan.net/{1}/futaba.php?mode=cat"
    futaba_thread_url: str = "https://{0}.2chan.net/{1}/res/{2}.htm"
    futaba_thread_json_url: str = (
        "https://{0}.2chan.net/{1}/futaba.php?mode=json&res={2}"
    )
    futaba_post_json_url: str = (
        "https://{0}.2chan.net/{1}/futaba.php?mode=json&start={2}&end={2}"
    )
    futaba_image_url_root: str = "https://{0}.2chan.net"
    futaba_bbsmenu_url: str = "https://www.2chan.net/bbsmenu.html"
    futaba_board_uri_pattern: str = r"\/\/(.*?)\.2chan\.net/(.*?)/(futaba|.*enter).htm"

    futaba_uploader_url_small: str = "http://dec.2chan.net/up2/src/\\1"
    futaba_uploader_url_large: str = "http://dec.2chan.net/up/src/\\1"
    futaba_uploader_small_re: str = r"(fu\d+\.(jpg|jpeg|png|gif|mp4|webp|webm))"
    futaba_uploader_large_re: str = r"(f\d+\.(jpg|jpeg|png|gif|mp4|webp|webm))"
