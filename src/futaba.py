import asyncio
import html
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Match
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from fastapi import HTTPException

from settings import Settings
from telemetry import log_event


@dataclass(slots=True)
class UpstreamResponse:
    status_code: int
    text: str


@dataclass(slots=True)
class UpstreamJsonResponse:
    status_code: int
    data: dict[str, Any] | None


@dataclass(slots=True)
class ThreadJsonResponse:
    status_code: int
    opener: dict[str, Any] | None
    thread: dict[str, Any] | None


class UpstreamResponseTooLarge(RuntimeError):
    pass


class RetryableUpstreamJsonError(RuntimeError):
    def __init__(
        self,
        detail: str,
        status_code: int = 502,
        retry_after_seconds: float | None = None,
    ):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


_BR_TAG_RE = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]*>", flags=re.DOTALL)
_RETRY_AFTER_SECONDS_RE = re.compile(r"あと(\d+)秒")
_JSON_FETCH_ATTEMPTS = 3
_JSON_FETCH_RETRY_DELAY_SECONDS = 0.25
_JSON_FETCH_RATE_LIMIT_MARGIN_SECONDS = 0.25


async def _read_limited_body(response, max_bytes: int) -> bytes:
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                raise UpstreamResponseTooLarge
        except ValueError:
            pass

    stream = response.js_response.body
    if stream is None:
        return b""

    reader = stream.getReader()
    body = bytearray()
    try:
        while True:
            result = await reader.read()
            if result.done:
                break

            chunk = bytes(result.value.to_py())
            if len(body) + len(chunk) > max_bytes:
                await reader.cancel("upstream response exceeded size limit")
                raise UpstreamResponseTooLarge
            body.extend(chunk)
    finally:
        reader.releaseLock()

    return bytes(body)


async def fetch_text(
    url: str, cookies: dict[str, str] | None = None
) -> UpstreamResponse:
    """Cloudflare Workers の Fetch API でふたばを取得する。"""
    from js import AbortSignal
    from pyodide.http import AbortError, pyfetch

    settings = Settings()
    started = time.perf_counter()
    headers = None
    if cookies:
        headers = {
            "Cookie": "; ".join(f"{key}={value}" for key, value in cookies.items())
        }

    target = urlparse(url)
    log_target = f"{target.netloc}{target.path}"

    signal = AbortSignal.timeout(settings.upstream_timeout_ms)
    try:
        response = await pyfetch(
            url,
            headers=headers,
            redirect="manual",
            signal=signal,
        )
        body = (
            await _read_limited_body(
                response,
                settings.upstream_max_response_bytes,
            )
            if int(response.status) == 200
            else b""
        )
    except UpstreamResponseTooLarge as exc:
        log_event(
            "upstream_fetch_failed",
            level="error",
            target=log_target,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            reason="response_too_large",
            max_bytes=settings.upstream_max_response_bytes,
        )
        raise HTTPException(
            status_code=502,
            detail="Upstream response exceeded the size limit",
        ) from exc
    except AbortError as exc:
        timed_out = bool(signal.aborted)
        log_event(
            "upstream_fetch_failed",
            level="error",
            target=log_target,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            reason="timeout" if timed_out else "network_error",
            error=str(exc),
        )
        raise HTTPException(
            status_code=504 if timed_out else 502,
            detail="Upstream request timed out"
            if timed_out
            else "Upstream request failed",
        ) from exc
    except Exception as exc:
        log_event(
            "upstream_fetch_failed",
            level="error",
            target=log_target,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            reason="unexpected_error",
            error_type=type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="Upstream request failed") from exc

    log_event(
        "upstream_fetch_completed",
        target=log_target,
        status=int(response.status),
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        response_bytes=len(body),
    )
    return UpstreamResponse(
        int(response.status), body.decode("cp932", errors="replace")
    )


async def _fetch_json_once(url: str) -> UpstreamJsonResponse:
    """Cloudflare Workers の Fetch API でUTF-8 JSONを1回取得する。"""
    from js import AbortSignal
    from pyodide.http import AbortError, pyfetch

    settings = Settings()
    started = time.perf_counter()
    target = urlparse(url)
    log_target = f"{target.netloc}{target.path}"
    signal = AbortSignal.timeout(settings.upstream_timeout_ms)

    try:
        response = await pyfetch(url, redirect="manual", signal=signal)
        status = int(response.status)
        body = (
            await _read_limited_body(
                response,
                settings.upstream_max_response_bytes,
            )
            if status == 200
            else b""
        )
    except UpstreamResponseTooLarge as exc:
        log_event(
            "upstream_fetch_failed",
            level="error",
            target=log_target,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            reason="response_too_large",
            max_bytes=settings.upstream_max_response_bytes,
        )
        raise HTTPException(
            status_code=502,
            detail="Upstream response exceeded the size limit",
        ) from exc
    except AbortError as exc:
        timed_out = bool(signal.aborted)
        log_event(
            "upstream_fetch_failed",
            level="error",
            target=log_target,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            reason="timeout" if timed_out else "network_error",
            error=str(exc),
        )
        if timed_out:
            raise HTTPException(
                status_code=504,
                detail="Upstream request timed out",
            ) from exc
        raise RetryableUpstreamJsonError("Upstream request failed") from exc
    except Exception as exc:
        log_event(
            "upstream_fetch_failed",
            level="error",
            target=log_target,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            reason="unexpected_error",
            error_type=type(exc).__name__,
        )
        raise RetryableUpstreamJsonError("Upstream request failed") from exc

    content_type = response.headers.get("content-type") or ""
    if status == 200 and "text/html" in content_type.lower():
        error_page = body.decode("cp932", errors="replace")
        retry_after_match = _RETRY_AFTER_SECONDS_RE.search(error_page)
        retry_after_seconds = (
            float(retry_after_match.group(1)) + _JSON_FETCH_RATE_LIMIT_MARGIN_SECONDS
            if retry_after_match
            else None
        )
        log_event(
            "upstream_fetch_failed",
            level="warning",
            target=log_target,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            reason="rate_limited" if retry_after_match else "unexpected_html",
            response_bytes=len(body),
            content_type=content_type,
            retry_after_seconds=retry_after_seconds,
        )
        raise RetryableUpstreamJsonError(
            "Upstream rate limited the request"
            if retry_after_match
            else "Upstream returned HTML instead of JSON",
            retry_after_seconds=retry_after_seconds,
        )

    data = None
    if status == 200:
        try:
            decoded = json.loads(body)
            if not isinstance(decoded, dict):
                raise ValueError("JSON root is not an object")
            data = decoded
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            error_context: dict[str, Any] = {
                "response_bytes": len(body),
                "content_type": content_type,
                "content_encoding": response.headers.get("content-encoding"),
            }
            if isinstance(exc, UnicodeDecodeError):
                error_context.update(
                    decode_offset=exc.start,
                    invalid_bytes=body[exc.start : min(len(body), exc.end + 8)].hex(),
                )
            log_event(
                "upstream_fetch_failed",
                level="error",
                target=log_target,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                reason="invalid_json",
                error_type=type(exc).__name__,
                **error_context,
            )
            raise RetryableUpstreamJsonError("Upstream returned invalid JSON") from exc

    log_event(
        "upstream_fetch_completed",
        target=log_target,
        status=status,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        response_bytes=len(body),
        document="json",
    )
    return UpstreamJsonResponse(status, data)


async def fetch_json(url: str) -> UpstreamJsonResponse:
    """UTF-8 JSONを取得し、一時的な上流障害だけを最大2回再試行する。"""
    target = urlparse(url)
    log_target = f"{target.netloc}{target.path}"
    last_error: RetryableUpstreamJsonError | None = None

    for attempt in range(1, _JSON_FETCH_ATTEMPTS + 1):
        try:
            response = await _fetch_json_once(url)
        except RetryableUpstreamJsonError as exc:
            last_error = exc
        else:
            if response.status_code not in {429, 500, 502, 503, 504}:
                return response
            last_error = RetryableUpstreamJsonError(
                f"Upstream returned HTTP {response.status_code}"
            )

        if attempt < _JSON_FETCH_ATTEMPTS:
            log_event(
                "upstream_fetch_retrying",
                level="warning",
                target=log_target,
                attempt=attempt,
                reason=last_error.detail,
            )
            retry_delay = _JSON_FETCH_RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
            if last_error.retry_after_seconds is not None:
                retry_delay = max(retry_delay, last_error.retry_after_seconds)
            await asyncio.sleep(retry_delay)

    if last_error is None:  # pragma: no cover - the loop always assigns or returns
        raise RuntimeError("JSON fetch retry loop ended without a result")
    raise HTTPException(
        status_code=last_error.status_code,
        detail=last_error.detail,
    ) from last_error


class FutabaBoard:
    async def get_and_parse(self, sub_domain: str, board_dir: str):
        # ふたば掲示板のスレッド一覧を取得しパースする
        html = await self.get(sub_domain, board_dir)
        return await self.parse_async(html)

    async def get(self, sub_domain: str, board_dir: str):
        setting = Settings()
        cookie = setting.futaba_catalog_view_cookie
        futaba_board_url = setting.futaba_board_url.format(sub_domain, board_dir)

        response = await fetch_text(futaba_board_url, cookies=cookie)
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Upstream returned HTTP {response.status_code}",
            )
        return response.text

    async def parse_async(self, text: str):
        started = time.perf_counter()
        try:
            parsed = self.parse(text)
        except Exception as exc:
            log_event(
                "html_parse_failed",
                level="error",
                document="board",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                input_chars=len(text),
                error_type=type(exc).__name__,
            )
            raise
        log_event(
            "html_parse_completed",
            document="board",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            input_chars=len(text),
            items=len(parsed),
        )
        return parsed

    def parse(self, text: str):
        """
        スレッド一覧のカタログから抽出するメソッド
        テーブルでまとまっているので結構簡単
        """
        bs = BeautifulSoup(text, "html.parser")

        # カタログテーブルの存在チェック
        cattable = bs.find("table", id="cattable")
        if not cattable:
            raise HTTPException(status_code=500, detail="カタログのHTML構造が異常です")

        threads = []
        for td in cattable.find_all("td"):
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
    async def get(
        self, sub_domain: str, board_dir: str, thread_id: str | int
    ) -> ThreadJsonResponse:
        """冒頭レスと返信のJSONを並列取得する。"""
        setting = Settings()
        opener_url = setting.futaba_post_json_url.format(
            sub_domain, board_dir, thread_id
        )
        thread_url = setting.futaba_thread_json_url.format(
            sub_domain, board_dir, thread_id
        )
        opener_response, thread_response = await asyncio.gather(
            fetch_json(opener_url),
            fetch_json(thread_url),
        )

        if thread_response.status_code != 200:
            status_code = thread_response.status_code
        else:
            status_code = opener_response.status_code
            opener_responses = (
                opener_response.data.get("res")
                if opener_response.data is not None
                else None
            )
            if (
                not isinstance(opener_responses, dict)
                or str(thread_id) not in opener_responses
            ):
                status_code = 404

        return ThreadJsonResponse(
            status_code=status_code,
            opener=opener_response.data,
            thread=thread_response.data,
        )

    async def get_incremental(
        self,
        sub_domain: str,
        board_dir: str,
        thread_id: str | int,
        start_post_no: int,
    ) -> UpstreamJsonResponse:
        """指定した投稿番号以降の返信と最新メタデータを取得する。"""
        setting = Settings()
        thread_url = setting.futaba_thread_incremental_json_url.format(
            sub_domain,
            board_dir,
            thread_id,
            start_post_no,
        )
        return await fetch_json(thread_url)

    async def parse_async(
        self,
        opener_data: dict[str, Any],
        thread_data: dict[str, Any],
        thread_id: str | int,
    ):
        started = time.perf_counter()
        try:
            parsed = self.parse(opener_data, thread_data, thread_id)
        except Exception as exc:
            log_event(
                "json_parse_failed",
                level="error",
                document="thread",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error_type=type(exc).__name__,
            )
            raise
        log_event(
            "json_parse_completed",
            document="thread",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            items=len(parsed["posts"]),
            posts_with_id=sum(bool(post["id"]) for post in parsed["posts"]),
        )
        return parsed

    def parse(
        self,
        opener_data: dict[str, Any],
        thread_data: dict[str, Any],
        thread_id: str | int,
    ):
        thread_id = str(thread_id)
        opener_responses = opener_data.get("res")
        replies = thread_data.get("res", {})
        if not isinstance(opener_responses, dict) or thread_id not in opener_responses:
            raise HTTPException(
                status_code=404, detail="スレッドの冒頭レスがありません"
            )
        if not isinstance(replies, dict):
            raise HTTPException(status_code=500, detail="スレッドのJSON構造が異常です")

        expire = thread_data.get("die")
        if not isinstance(expire, str) or not expire:
            raise HTTPException(status_code=500, detail="スレッド期限情報がありません")

        sod_values = thread_data.get("sd")
        if not isinstance(sod_values, dict):
            sod_values = {}

        all_posts = [(thread_id, opener_responses[thread_id]), *replies.items()]
        thread = {"posts": []}
        thread_res_dict: dict[str, int] = {}
        for index, (post_no, post_data) in enumerate(all_posts, start=1):
            if not isinstance(post_data, dict):
                raise HTTPException(
                    status_code=500, detail="スレッドの投稿JSON構造が異常です"
                )
            thread["posts"].append(
                self._parse_post(
                    index, str(post_no), post_data, sod_values, thread_res_dict
                )
            )

        thread["title"] = thread["posts"][0]["body"].replace("<br>", " ")
        thread["expire"] = f"{expire}頃消えます"
        return thread

    def _parse_post(
        self,
        i: int,
        post_no: str,
        post_data: dict[str, Any],
        sod_values: dict[str, Any],
        thread_res_dict: dict[str, int],
    ) -> dict[str, Any]:
        body = self._comment_to_text(str(post_data.get("com") or ""))
        deletion_notice = {
            "del": "スレッドを立てた人によって削除されました",
            "del2": "削除依頼によって隔離されました",
        }.get(post_data.get("del"))
        if deletion_notice:
            body = f"{deletion_notice}<br>{body}" if body else deletion_notice
        image = post_data.get("src") or None
        image_filename = os.path.basename(urlparse(str(image)).path) if image else None
        poster_id = post_data.get("id") or post_data.get("host") or None
        sod_count = sod_values.get(post_no)
        post = {
            "title": post_data.get("sub") or None,
            "image": image,
            "name": post_data.get("name") or None,
            "mail": post_data.get("email") or None,
            "date": str(post_data.get("now") or ""),
            "id": poster_id,
            "no": f"No.{post_no}",
            "sod": f"そうだねx{sod_count}" if sod_count is not None else "+",
            "body": body,
        }

        body_by_lines = body.split("<br>")
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

        # ChMateで引用文の数字がレス番号として誤認されることを防ぐため、
        # 連続する引用符(>)の後にスペースを挿入する処理を追加
        body_lines = body.split("<br>")
        processed_lines = []
        for line in body_lines:
            # 行頭の連続する>の後に続く文字列にスペースを挿入
            # >>, >>>, >>>>... の後に数字や文字が続く場合を対象とする
            processed_line = re.sub(r"^(>+)([^>\s].*)", r"\1 \2", line)
            processed_lines.append(processed_line)
        post["body"] = "<br>".join(processed_lines)

        return post

    @staticmethod
    def _comment_to_text(comment: str) -> str:
        """ふたばJSONの本文HTML断片を従来の本文形式へ変換する。"""
        lines = _BR_TAG_RE.split(comment)
        return "<br>".join(
            html.unescape(_HTML_TAG_RE.sub("", line)).strip() for line in lines
        ).strip()
