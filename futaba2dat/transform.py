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
