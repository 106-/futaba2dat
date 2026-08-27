import pytest
from fastapi import HTTPException

from futaba import (
    FutabaBoard,
    FutabaThread,
    RetryableUpstreamJsonError,
    UpstreamJsonResponse,
    UpstreamResponse,
    UpstreamResponseTooLarge,
    _read_limited_body,
    fetch_json,
)


class _FakeChunk:
    def __init__(self, value: bytes):
        self.value = value

    def to_py(self):
        return self.value


class _FakeReadResult:
    def __init__(self, value: bytes | None = None):
        self.done = value is None
        self.value = _FakeChunk(value) if value is not None else None


class _FakeReader:
    def __init__(self, chunks: list[bytes]):
        self.chunks = iter(chunks)
        self.cancelled = False
        self.released = False

    async def read(self):
        return _FakeReadResult(next(self.chunks, None))

    async def cancel(self, _reason: str):
        self.cancelled = True

    def releaseLock(self):
        self.released = True


class _FakeStream:
    def __init__(self, reader: _FakeReader):
        self.reader = reader

    def getReader(self):
        return self.reader


class _FakeResponse:
    def __init__(self, chunks: list[bytes], content_length: str | None = None):
        self.reader = _FakeReader(chunks)
        self.js_response = type(
            "JsResponse",
            (),
            {"body": _FakeStream(self.reader)},
        )()
        self.headers = {}
        if content_length is not None:
            self.headers["content-length"] = content_length


@pytest.mark.asyncio
async def test_read_limited_body():
    response = _FakeResponse([b"abc", b"def"])
    assert await _read_limited_body(response, 6) == b"abcdef"
    assert response.reader.released


@pytest.mark.asyncio
async def test_read_limited_body_rejects_large_stream():
    response = _FakeResponse([b"abc", b"def"])
    with pytest.raises(UpstreamResponseTooLarge):
        await _read_limited_body(response, 5)
    assert response.reader.cancelled
    assert response.reader.released


@pytest.mark.asyncio
async def test_read_limited_body_rejects_large_content_length():
    response = _FakeResponse([], content_length="6")
    with pytest.raises(UpstreamResponseTooLarge):
        await _read_limited_body(response, 5)


@pytest.mark.asyncio
async def test_board_maps_upstream_error_to_bad_gateway(monkeypatch):
    async def fake_fetch_text(*_args, **_kwargs):
        return UpstreamResponse(status_code=503, text="")

    monkeypatch.setattr("futaba.fetch_text", fake_fetch_text)
    with pytest.raises(HTTPException) as exc_info:
        await FutabaBoard().get("may", "b")
    assert exc_info.value.status_code == 502


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


def test_futaba_thread_json() -> None:
    opener = {
        "res": {
            "000000000": {
                "now": "21/01/01(金)00:00:00",
                "name": "投稿者名",
                "email": "mail@example.jp",
                "sub": "題名",
                "com": "本文1<br>本文2",
                "id": "ID:XXXXXXXX",
                "src": "/b/src/0000000000000.jpg",
            }
        }
    }
    replies = {
        "die": "00:00",
        "sd": {"000000002": "3"},
        "res": {
            "000000001": {
                "now": "21/01/01(金)00:00:00",
                "name": "投稿者名",
                "email": "",
                "sub": "題名",
                "com": "引用",
                "id": "ID:xxxxxxxx",
                "src": "",
            },
            "000000002": {
                "now": "21/01/01(金)00:00:00",
                "name": "投稿者名",
                "email": "",
                "sub": "題名",
                "com": '<font color="#789922">&gt;引用</font><br>本文',
                "id": "ID:xxxxxxxx",
                "src": "",
            },
            "000000003": {
                "now": "21/01/01(金)00:00:00",
                "name": "投稿者名",
                "email": "",
                "sub": "題名",
                "com": "画像あり本文",
                "id": "ID:xxxxxxxx",
                "src": "/b/src/0000000000003.jpg",
                "del": "del2",
            },
            "000000004": {
                "now": "21/01/01(金)00:00:00",
                "name": "投稿者名",
                "email": "",
                "sub": "題名",
                "com": '<font color="#789922">&gt;0000000000003.jpg</font><br>画像引用',
                "id": "ID:xxxxxxxx",
                "src": "",
            },
        },
    }
    thread = FutabaThread().parse(opener, replies, "000000000")
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
                "sod": "そうだねx3",
                "body": "> 引用<br>本文",
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
                "body": "削除依頼によって隔離されました<br>画像あり本文",
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
                "body": "> 0000000000003.jpg<br>画像引用",
                "quote_res": [4],
            },
        ],
    }
    assert thread == expected


def test_futaba_thread_json_without_replies() -> None:
    opener = {
        "res": {
            "123": {
                "now": "26/08/26(水)00:00:00",
                "name": "名無し",
                "email": "",
                "sub": "無題",
                "com": "本文",
                "id": "",
                "src": "",
            }
        }
    }
    thread = FutabaThread().parse(opener, {"die": "00:00", "sd": []}, "123")

    assert len(thread["posts"]) == 1
    assert thread["posts"][0]["no"] == "No.123"


def test_futaba_thread_json_uses_host_when_id_is_empty() -> None:
    opener = {
        "res": {
            "0000000": {
                "now": "21/01/01(金)00:00:00",
                "name": "",
                "email": "",
                "sub": "",
                "com": "本文1<br>本文2",
                "id": "",
                "host": "IP:0.0.*(sample.ne.jp)",
                "src": "/9/src/0000000000000.jpg",
            }
        }
    }
    replies = {
        "die": "1月1日",
        "sd": [],
        "res": {
            "0000001": {
                "now": "21/01/01(金)00:00:00",
                "name": "",
                "email": "",
                "sub": "",
                "com": "画像あり本文",
                "id": "",
                "host": "IP:0.0.*(sample.ne.jp)",
                "src": "/9/src/0000000000001.jpg",
            },
            "0000002": {
                "now": "21/01/01(金)00:00:00",
                "name": "",
                "email": "",
                "sub": "",
                "com": "画像なし本文",
                "id": "",
                "host": "IP:0.0.*(sample.ne.jp)",
                "src": "",
            },
            "0000003": {
                "now": "21/01/01(金)00:00:00",
                "name": "",
                "email": "",
                "sub": "",
                "com": "画像あり本文3",
                "id": "",
                "host": "IP:0.0.*(sample.ne.jp)",
                "src": "/9/src/0000000000003.jpg",
            },
        },
    }
    thread = FutabaThread().parse(opener, replies, "0000000")
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
    assert thread == expected


@pytest.mark.asyncio
async def test_futaba_thread_fetches_opener_and_replies_in_parallel(monkeypatch):
    requested_urls = []

    async def fake_fetch_json(url):
        requested_urls.append(url)
        if "&res=" in url:
            return UpstreamJsonResponse(200, {"die": "00:00", "res": {}, "sd": {}})
        return UpstreamJsonResponse(200, {"res": {"123": {"com": "本文"}}})

    monkeypatch.setattr("futaba.fetch_json", fake_fetch_json)
    response = await FutabaThread().get("may", "b", 123)

    assert response.status_code == 200
    assert len(requested_urls) == 2
    assert any("mode=json&res=123" in url for url in requested_urls)
    assert any("mode=json&start=123&end=123" in url for url in requested_urls)


@pytest.mark.asyncio
async def test_futaba_thread_missing_opener_is_not_found(monkeypatch):
    async def fake_fetch_json(url):
        if "&res=" in url:
            return UpstreamJsonResponse(200, {"die": "00:00", "res": {}, "sd": {}})
        return UpstreamJsonResponse(200, {"res": {}})

    monkeypatch.setattr("futaba.fetch_json", fake_fetch_json)
    response = await FutabaThread().get("may", "b", 123)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_fetch_json_retries_invalid_response(monkeypatch):
    attempts = 0
    retry_delays = []

    async def fake_fetch_json_once(_url):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RetryableUpstreamJsonError("Upstream returned invalid JSON")
        return UpstreamJsonResponse(200, {"res": {}})

    async def fake_sleep(delay):
        retry_delays.append(delay)

    monkeypatch.setattr("futaba._fetch_json_once", fake_fetch_json_once)
    monkeypatch.setattr("futaba.asyncio.sleep", fake_sleep)

    response = await fetch_json("https://may.2chan.net/b/futaba.php?mode=json")

    assert response.status_code == 200
    assert attempts == 2
    assert retry_delays == [0.25]


@pytest.mark.asyncio
async def test_fetch_json_honors_upstream_retry_after(monkeypatch):
    attempts = 0
    retry_delays = []

    async def fake_fetch_json_once(_url):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RetryableUpstreamJsonError(
                "Upstream rate limited the request",
                retry_after_seconds=2.25,
            )
        return UpstreamJsonResponse(200, {"res": {}})

    async def fake_sleep(delay):
        retry_delays.append(delay)

    monkeypatch.setattr("futaba._fetch_json_once", fake_fetch_json_once)
    monkeypatch.setattr("futaba.asyncio.sleep", fake_sleep)

    response = await fetch_json("https://may.2chan.net/b/futaba.php?mode=json")

    assert response.status_code == 200
    assert attempts == 2
    assert retry_delays == [2.25]


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


def test_futaba_thread_missing_opener() -> None:
    thread = FutabaThread()
    with pytest.raises(HTTPException) as exc_info:
        thread.parse({"res": {}}, {"die": "00:00", "res": {}}, "123")

    assert exc_info.value.status_code == 404
    assert "冒頭レス" in str(exc_info.value.detail)


def test_futaba_thread_missing_expiry() -> None:
    thread = FutabaThread()
    with pytest.raises(HTTPException) as exc_info:
        thread.parse({"res": {"123": {"com": "本文"}}}, {"res": {}}, "123")

    assert exc_info.value.status_code == 500
    assert "期限情報" in str(exc_info.value.detail)
