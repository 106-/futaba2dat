import os
import re
from typing import Match
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from futaba2dat.settings import Settings


class FutabaBoard:
    def get_and_parse(self, sub_domain: str, board_dir: str):
        # ふたば掲示板のスレッド一覧を取得しパースする
        html = self.get(sub_domain, board_dir)
        return self.parse(html)

    def get(self, sub_domain: str, board_dir: str):
        setting = Settings()
        cookie = setting.futaba_catalog_view_cookie
        futaba_board_url = setting.futaba_board_url.format(sub_domain, board_dir)
        return requests.get(futaba_board_url, cookies=cookie).text

    def parse(self, text: str):
        """
        スレッド一覧のカタログから抽出するメソッド
        テーブルでまとまっているので結構簡単
        """
        bs = BeautifulSoup(text, "html.parser")

        threads = []
        for td in bs.find("table", id="cattable").find_all("td"):
            id_match: Match[str] = re.match(r"res/(\d+?)\.htm", td.a.get("href"))
            if not id_match:
                # スレッドIDが見つからない場合はスキップ
                continue
            id = id_match.group(1)
            if td.a.img:
                imageurl = td.a.img.get("src")
            else:
                imageurl = None
            title = td.small.get_text()

            # "()" で括られてるので[1:-1]で省く
            count = int(td.find("font", size="2").get_text()[1:-1])
            threads.append(
                {"id": id, "image_url": imageurl, "title": title, "count": count}
            )
        return threads


class FutabaThread:
    def get(self, sub_domain: str, board_dir: str, thread_id: str):
        # ふたば掲示板のスレッド一覧を取得しパースする
        setting = Settings()
        return requests.get(
            setting.futaba_thread_url.format(sub_domain, board_dir, thread_id)
        )

    def parse(self, text: str):
        bs = BeautifulSoup(text, "html.parser")
        thread_bs = bs.find("div", class_="thre")
        thread = {"posts": []}
        thread_res_dict = {}

        # スレッドを立てた人の投稿を抽出
        thread["posts"].append(self._parse_post(1, thread_bs, thread_res_dict))

        # スレッドタイトルをスレを立てた人のものにする
        # これは `<br>` タグを含んでいるのでそれを空白文字にしておく必要がある.
        thread["title"] = thread["posts"][0]["body"].replace("<br>", " ")

        # スレッドが消える時刻を抽出する 例:"00:00頃消えます"
        thread["expire"] = bs.find("span", class_="cntd").get_text(strip=True)

        for i, post in enumerate(bs.find_all("table", border=0), start=2):
            thread["posts"].append(self._parse_post(i, post, thread_res_dict))

        return thread

    def _parse_post(self, i, post_bs, thread_res_dict):
        """
        スレッドに付いた投稿一件一件を注意深くパースする関数
        これは投稿者による投稿も含む
        """
        post = {}

        def get_span_text(span_attr):
            tag = post_bs.find("span", class_=span_attr)
            if tag:
                return tag.get_text(strip=True)
            else:
                None

        def gettext_strip(x):
            return x.get_text(strip=True)

        # `csb` は投稿の題名を持つタグに含まれる属性
        post["title"] = get_span_text("csb")

        # 投稿に含まれる画像を抽出. 含まれないこともある.
        image_filename = None
        if post_bs.find("img"):
            post["image"] = post_bs.find("a", target="_blank").get("href")
            image_filename = os.path.basename(urlparse(post["image"]).path)
        else:
            post["image"] = None

        # `cnm` は投稿者名を含むタグ. 投稿者はメールアドレスを指定している場合がある.
        # `<a>` タグを持っているかどうかで分岐させる.
        name = post_bs.find("span", class_="cnm")
        if name and name.find("a"):
            # `mailto:` 形式なのでメールアドレスのみを抽出する.
            post["name"] = gettext_strip(name)
            post["mail"] = name.a.get("href").split(":")[1]
        elif name:
            post["name"] = gettext_strip(name)
            post["mail"] = None
        else:
            post["name"] = None
            post["mail"] = None

        # `cnw` は投稿日時とIDを持つタグ. 2つはスペースで区切られている.
        # しかしふたばではIDを持たないスレッドの方が多いため確認をしておく必要がある.
        date_and_id = get_span_text("cnw")
        date_and_id_splitted = date_and_id.split(" ")
        if len(date_and_id_splitted) > 1:
            post["date"] = date_and_id_splitted[0]
            post["id"] = date_and_id_splitted[1]
        else:
            post["date"] = date_and_id_splitted[0]
            post["id"] = None

        # `cno` は投稿番号を含むもの. 例: "No.000000000"
        post["no"] = get_span_text("cno")

        # 投稿への"そうだね"を抽出
        post["sod"] = gettext_strip(post_bs.find("a", class_="sod"))

        # 投稿の本文 DAT形式する都合上 `<br>` タグを含んだ状態で取っておきたい.
        # のでタグの要素ごとに区切り文字を注入できる `separator` オプションを使う.
        post["body"] = post_bs.find("blockquote").get_text(separator="<br>", strip=True)

        body_by_lines = post["body"].split("<br>")
        # 引用レスのレス番号を取得して記録する。
        post["quote_res"] = []
        for line in body_by_lines:
            quote_res = re.match(r"^>(?!>)(.+)", line)
            if (
                quote_res
                and quote_res.group(1) in thread_res_dict
                and thread_res_dict[quote_res.group(1)] not in post["quote_res"]
            ):
                post["quote_res"].append(thread_res_dict[quote_res.group(1)])

        # 引用レスがあったとき引用内容からレス番号が引けるようにしたい。
        # そのためにレスの行をkey, レス番号をvalueとする辞書を作成する。
        # 同じ行が複数のレスに含まれたらもちろん壊れるが、そこまでの正確性はおいておく。
        for line in body_by_lines:
            thread_res_dict[line] = i

        # 投稿番号でも引けるようにする。
        thread_res_dict[post["no"]] = i

        # 画像ファイル名でも引けるようにする。
        if image_filename:
            thread_res_dict[image_filename] = i

        return post
