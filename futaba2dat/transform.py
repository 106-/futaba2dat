import re

from futaba2dat.settings import Settings


# ふたばアップローダー上のファイルを表す文字列をURLに変換する
def futaba_uploader(thread):
    settings = Settings()

    for i, post in enumerate(thread["posts"]):
        thread["posts"][i]["body"] = re.sub(
            settings.futaba_uploader_small_re,
            settings.futaba_uploader_url_small,
            thread["posts"][i]["body"],
        )
        thread["posts"][i]["body"] = re.sub(
            settings.futaba_uploader_large_re,
            settings.futaba_uploader_url_large,
            thread["posts"][i]["body"],
        )

    return thread


def convert_futaba_urls_to_2ch_format(thread: dict, proxy_domain: str) -> dict:
    """ふたばちゃんねるURLを2ch形式URLに変換する"""
    # パターン: http://may.2chan.net/b/res/12345.htm または https://may.2chan.net/b/res/12345.htm
    futaba_url_pattern = r'https?://([^.]+)\.2chan\.net/([^/]+)/res/(\d+)\.htm'
    
    def replace_url(match):
        subdomain = match.group(1)  # may
        board = match.group(2)      # b  
        thread_id = match.group(3)  # 12345
        return f"http://{proxy_domain}/test/read.cgi/{subdomain}/{board}/{thread_id}/"
    
    for post in thread["posts"]:
        post["body"] = re.sub(futaba_url_pattern, replace_url, post["body"])
    
    return thread
