import json

import pytest
from fastapi import HTTPException

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
                "quote_res": [],
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
                "body": "引用",
                "quote_res": [],
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
                "quote_res": [2],
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
                "quote_res": [],
            },
            {
                "title": "題名",
                "image": None,
                "name": "投稿者名",
                "mail": None,
                "date": "21/01/01(金)00:00:00",
                "id": "ID:xxxxxxxx",
                "no": "No.000000004",
                "sod": "+",
                "body": ">0000000000003.jpg<br>画像引用",
                "quote_res": [4],
            },
        ],
    }
    assert thread == expected


def test_futaba_thread2() -> None:
    html = open("./tests/testcase_thread2.html", "r").read()
    thread = FutabaThread().parse(html)
    expected = {
        "title": "本文1 本文2",
        "expire": "1月1日頃消えます",
        "posts": [
            {
                "title": None,
                "image": "/9/src/0000000000000.jpg",
                "name": None,
                "mail": None,
                "date": "21/01/01(金)00:00:00",
                "id": "IP:0.0.*(sample.ne.jp)",
                "no": "No.0000000",
                "sod": "+",
                "body": "本文1<br>本文2",
                "quote_res": [],
            },
            {
                "title": None,
                "image": "/9/src/0000000000001.jpg",
                "name": None,
                "mail": None,
                "date": "21/01/01(金)00:00:00",
                "id": "IP:0.0.*(sample.ne.jp)",
                "no": "No.0000001",
                "sod": "+",
                "body": "画像あり本文",
                "quote_res": [],
            },
            {
                "title": None,
                "image": None,
                "name": None,
                "mail": None,
                "date": "21/01/01(金)00:00:00",
                "id": "IP:0.0.*(sample.ne.jp)",
                "no": "No.0000002",
                "sod": "+",
                "body": "画像なし本文",
                "quote_res": [],
            },
            {
                "title": None,
                "image": "/9/src/0000000000003.jpg",
                "name": None,
                "mail": None,
                "date": "21/01/01(金)00:00:00",
                "id": "IP:0.0.*(sample.ne.jp)",
                "no": "No.0000003",
                "sod": "+",
                "body": "画像あり本文3",
                "quote_res": [],
            },
        ],
    }
    print(json.dumps(thread, indent=2))
    assert thread == expected


def test_futaba_board_missing_cattable() -> None:
    """cattableが存在しない異常なHTMLでHTTPExceptionが発生することをテスト"""
    # cattableがないHTML
    malformed_html = """
    <html>
    <body>
        <div>何かのコンテンツ</div>
        <table id="other_table">
            <td>関係ないテーブル</td>
        </table>
    </body>
    </html>
    """

    board = FutabaBoard()
    with pytest.raises(HTTPException) as exc_info:
        board.parse(malformed_html)

    assert exc_info.value.status_code == 500
    assert "カタログのHTML構造が異常です" in str(exc_info.value.detail)


def test_futaba_thread_missing_thre() -> None:
    """thre要素が存在しない異常なHTMLでHTTPExceptionが発生することをテスト"""
    # thre要素がないHTML
    malformed_html = """
    <html>
    <body>
        <div class="other">何かのコンテンツ</div>
        <span class="cntd">00:00頃消えます</span>
    </body>
    </html>
    """

    thread = FutabaThread()
    with pytest.raises(HTTPException) as exc_info:
        thread.parse(malformed_html)

    assert exc_info.value.status_code == 500
    assert "スレッドのHTML構造が異常です" in str(exc_info.value.detail)


def test_futaba_thread_missing_cntd() -> None:
    """cntd要素が存在しない異常なHTMLでHTTPExceptionが発生することをテスト"""
    # cntd要素がないが、thre要素は存在するHTML
    malformed_html = """
    <html>
    <body>
        <div class="thre">
            <span class="csb">題名</span>
            <span class="cnm">投稿者名</span>
            <span class="cnw">21/01/01(金)00:00:00 ID:XXXXXXXX</span>
            <span class="cno">No.000000000</span>
            <a class="sod">+</a>
            <blockquote>本文</blockquote>
        </div>
        <!-- cntd要素が存在しない -->
        <div class="other">何かのコンテンツ</div>
    </body>
    </html>
    """

    thread = FutabaThread()
    with pytest.raises(HTTPException) as exc_info:
        thread.parse(malformed_html)

    assert exc_info.value.status_code == 500
    assert "スレッド期限情報のHTML構造が異常です" in str(exc_info.value.detail)
