import json
import re

import requests
from bs4 import BeautifulSoup

from futaba2dat.settings import Settings

text = requests.get(Settings().futaba_bbsmenu_url).text
bs = BeautifulSoup(text, "html.parser")

format = re.compile(Settings().futaba_board_uri_pattern)
boards = []
for b in bs.find_all(href=format):
    groups = format.match(b.get("href")).groups()
    boards.append([groups[0], groups[1], b.get_text()])

json.dump(boards, open("./futaba2dat/boards.json", "w+"), indent=2, ensure_ascii=False)
