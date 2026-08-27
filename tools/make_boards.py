import json
import re
from difflib import unified_diff
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from src.settings import Settings

BOARDS_PATH = Path(__file__).parents[1] / "src" / "boards.json"


def fetch_bbsmenu() -> str:
    settings = Settings()
    request = Request(settings.futaba_bbsmenu_url, headers={"User-Agent": "futaba2dat"})
    with urlopen(request, timeout=30) as response:
        encoding = response.headers.get_content_charset() or "cp932"
        return response.read().decode(encoding, errors="replace")


def main() -> None:
    settings = Settings()
    bs = BeautifulSoup(fetch_bbsmenu(), "html.parser")
    board_pattern = re.compile(settings.futaba_board_uri_pattern)
    boards = []
    for board in bs.find_all(href=board_pattern):
        groups = board_pattern.search(board.get("href")).groups()
        name = board.get_text()
        if "二次元裏" in name:
            name = f"{name}({groups[0]})"
        boards.append([groups[0], groups[1], name])

    boards.extend([["img", "b", "二次元裏(img)"], ["dat", "b", "二次元裏(dat)"]])
    new_content = json.dumps(boards, indent=2, ensure_ascii=False) + "\n"
    old_content = BOARDS_PATH.read_text(encoding="utf-8")
    diff = list(
        unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="boards.json (現在)",
            tofile="boards.json (新規)",
        )
    )

    print("".join(diff) if diff else "変更なし")
    BOARDS_PATH.write_text(new_content, encoding="utf-8")


if __name__ == "__main__":
    main()
