import json
import re
from difflib import unified_diff

import requests
from bs4 import BeautifulSoup

from futaba2dat.settings import Settings

text = requests.get(Settings().futaba_bbsmenu_url).text
bs = BeautifulSoup(text, "html.parser")

format = re.compile(Settings().futaba_board_uri_pattern)
boards = []
for b in bs.find_all(href=format):
    groups = format.search(b.get("href")).groups()
    name = b.get_text()
    if "二次元裏" in name:
        name = f"{name}({groups[0]})"
    boards.append([groups[0], groups[1], name])

hidden_boards = [["img", "b", "二次元裏(img)"], ["dat", "b", "二次元裏(dat)"]]
boards.extend(hidden_boards)

boards_path = "./futaba2dat/boards.json"
new_content = json.dumps(boards, indent=2, ensure_ascii=False) + "\n"

try:
    old_content = open(boards_path).read()
except FileNotFoundError:
    old_content = ""

diff = list(
    unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile="boards.json (現在)",
        tofile="boards.json (新規)",
    )
)

if diff:
    print("".join(diff))
else:
    print("変更なし")

open(boards_path, "w").write(new_content)
