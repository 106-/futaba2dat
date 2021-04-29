import json

from futaba2dat import futaba
from futaba2dat.futaba import FutabaBoard, FutabaThread


def test_futaba_board1() -> None:
    html = open("./tests/testcase_board1.html", "r").read()
    board = FutabaBoard().parse(html)
    expected = [
        {
            "id": "000000001",
            "image_url": "/b/thumb/0000000000001s.jpg",
            "title": "タイトル1",
            "count": 10,
        },
        {
            "id": "000000002",
            "image_url": "/b/thumb/0000000000002s.jpg",
            "title": "タイトル2",
            "count": 20,
        },
        {
            "id": "000000003",
            "image_url": "/b/thumb/0000000000003s.jpg",
            "title": "タイトル3",
            "count": 30,
        },
        {
            "id": "000000004",
            "image_url": "/b/thumb/0000000000004s.jpg",
            "title": "タイトル4",
            "count": 40,
        },
        {
            "id": "000000005",
            "image_url": "/b/thumb/0000000000005s.jpg",
            "title": "タイトル5",
            "count": 50,
        },
        {
            "id": "000000006",
            "image_url": "/b/thumb/0000000000006s.jpg",
            "title": "タイトル6",
            "count": 60,
        },
    ]
    assert board == expected


def test_futaba_thread1() -> None:
    html = open("./tests/testcase_thread1.html", "r").read()
    thread = FutabaThread().parse(html)
    expected = {
        "title": "本文1 本文2",
        "expire": "00:00頃消えます",
        "posts": [
            {
                "title": "題名",
                "image": "/b/src/0000000000000.jpg",
                "name": "投稿者名",
                "mail": "mail@example.jp",
                "date": "21/01/01(金)00:00:00",
                "id": "ID:XXXXXXXX",
                "no": "No.000000000",
                "sod": "+",
                "body": "本文1<br>本文2",
            },
            {
                "title": "題名",
                "image": None,
                "name": "投稿者名",
                "mail": None,
                "date": "21/01/01(金)00:00:00",
                "id": "ID:xxxxxxxx",
                "no": "No.000000001",
                "sod": "+",
                "body": "本文",
            },
            {
                "title": "題名",
                "image": None,
                "name": "投稿者名",
                "mail": None,
                "date": "21/01/01(金)00:00:00",
                "id": "ID:xxxxxxxx",
                "no": "No.000000002",
                "sod": "+",
                "body": ">引用<br>本文",
            },
            {
                "title": "題名",
                "image": "/b/src/0000000000003.jpg",
                "name": "投稿者名",
                "mail": None,
                "date": "21/01/01(金)00:00:00",
                "id": "ID:xxxxxxxx",
                "no": "No.000000003",
                "sod": "+",
                "body": "画像あり本文",
            },
        ],
    }
    print(json.dumps(thread, indent=2))
    assert thread == expected
