import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

from js import Request as JsRequest
from js import Response as JsResponse
from js import caches

from futaba import FutabaThread, ThreadJsonResponse
from settings import Settings
from telemetry import log_event

_CACHE_SCHEMA_VERSION = 1
_CACHE_KEY_PREFIX = "/.futaba2dat-cache/thread-state/v1"


@dataclass(frozen=True, slots=True)
class CachedThreadState:
    opener: dict[str, Any]
    thread: dict[str, Any]
    last_full_sync_ms: int
    hot: bool

    @property
    def reply_count(self) -> int:
        replies = self.thread.get("res")
        return len(replies) if isinstance(replies, dict) else 0

    @property
    def last_reply_no(self) -> int | None:
        replies = self.thread.get("res")
        if not isinstance(replies, dict) or not replies:
            return None
        try:
            return max(int(post_no) for post_no in replies)
        except (TypeError, ValueError):
            return None

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": _CACHE_SCHEMA_VERSION,
                "opener": self.opener,
                "thread": self.thread,
                "last_full_sync_ms": self.last_full_sync_ms,
                "hot": self.hot,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, serialized: str) -> "CachedThreadState":
        payload = json.loads(serialized)
        if not isinstance(payload, dict):
            raise ValueError("cache payload is not an object")
        if payload.get("version") != _CACHE_SCHEMA_VERSION:
            raise ValueError("cache schema version does not match")

        opener = payload.get("opener")
        thread = payload.get("thread")
        last_full_sync_ms = payload.get("last_full_sync_ms")
        hot = payload.get("hot")
        if not isinstance(opener, dict) or not isinstance(thread, dict):
            raise ValueError("cache thread data is invalid")
        if isinstance(last_full_sync_ms, bool) or not isinstance(
            last_full_sync_ms, int
        ):
            raise ValueError("cache timestamp is invalid")
        if not isinstance(hot, bool):
            raise ValueError("cache stage is invalid")
        return cls(
            opener=opener,
            thread=thread,
            last_full_sync_ms=last_full_sync_ms,
            hot=hot,
        )


class ThreadStateStore(Protocol):
    async def get(self, cache_url: str) -> CachedThreadState | None: ...

    async def put(
        self, cache_url: str, state: CachedThreadState, ttl_seconds: int
    ) -> None: ...

    async def delete(self, cache_url: str) -> None: ...


class CloudflareThreadStateStore:
    """Cache APIを、消失しても復元可能なスレッド状態ストアとして使う。"""

    async def get(self, cache_url: str) -> CachedThreadState | None:
        started = time.perf_counter()
        try:
            response = await caches.default.match(JsRequest.new(cache_url))
            if response is None:
                return None
            state = CachedThreadState.from_json(str(await response.text()))
        except Exception as exc:
            log_event(
                "thread_cache_read_failed",
                level="warning",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error_type=type(exc).__name__,
            )
            return None

        log_event(
            "thread_cache_read_completed",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            reply_count=state.reply_count,
            stage="hot" if state.hot else "candidate",
        )
        return state

    async def put(
        self, cache_url: str, state: CachedThreadState, ttl_seconds: int
    ) -> None:
        started = time.perf_counter()
        serialized = state.to_json()
        try:
            response = JsResponse.new(serialized)
            response.headers.set("Cache-Control", f"s-maxage={ttl_seconds}")
            response.headers.set("Content-Type", "application/json; charset=utf-8")
            await caches.default.put(JsRequest.new(cache_url), response)
        except Exception as exc:
            log_event(
                "thread_cache_write_failed",
                level="warning",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error_type=type(exc).__name__,
            )
            return

        log_event(
            "thread_cache_write_completed",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            cache_bytes=len(serialized.encode("utf-8")),
            reply_count=state.reply_count,
            stage="hot" if state.hot else "candidate",
            ttl_seconds=ttl_seconds,
        )

    async def delete(self, cache_url: str) -> None:
        try:
            await caches.default.delete(JsRequest.new(cache_url))
        except Exception as exc:
            log_event(
                "thread_cache_delete_failed",
                level="warning",
                error_type=type(exc).__name__,
            )


def build_thread_cache_url(
    request_url: str,
    sub_domain: str,
    board_dir: str,
    thread_id: str | int,
) -> str:
    request_parts = urlsplit(request_url)
    return (
        f"{request_parts.scheme}://{request_parts.netloc}{_CACHE_KEY_PREFIX}/"
        f"{sub_domain}/{board_dir}/{thread_id}"
    )


def merge_incremental_thread(
    cached_thread: dict[str, Any], incremental_thread: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    """増分レスを追加し、sd等のメタデータは最新値で置き換える。"""
    expire = incremental_thread.get("die")
    if not isinstance(expire, str) or not expire:
        raise ValueError("incremental response has no expiry")

    sod_values = incremental_thread.get("sd")
    if not isinstance(sod_values, (dict, list)):
        raise ValueError("incremental response has no sodane values")

    incremental_replies = incremental_thread.get("res", {})
    if not isinstance(incremental_replies, dict):
        raise ValueError("incremental replies are invalid")
    cached_replies = cached_thread.get("res", {})
    if not isinstance(cached_replies, dict):
        raise ValueError("cached replies are invalid")

    merged = dict(cached_thread)
    for key, value in incremental_thread.items():
        if key != "res":
            merged[key] = value
    merged["res"] = {**cached_replies, **incremental_replies}
    return merged, len(incremental_replies)


class ThreadCacheCoordinator:
    def __init__(
        self,
        store: ThreadStateStore,
        *,
        client: FutabaThread | None = None,
        settings: Settings | None = None,
        clock_ms: Callable[[], int] | None = None,
    ):
        self.store = store
        self.client = client or FutabaThread()
        self.settings = settings or Settings()
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))

    async def get(
        self,
        request_url: str,
        sub_domain: str,
        board_dir: str,
        thread_id: str | int,
    ) -> ThreadJsonResponse:
        started = time.perf_counter()
        cache_url = build_thread_cache_url(
            request_url, sub_domain, board_dir, thread_id
        )
        state = await self.store.get(cache_url)
        now_ms = self.clock_ms()

        if state is None:
            response = await self.client.get(sub_domain, board_dir, thread_id)
            cache_status = await self._store_full_response(
                cache_url,
                response,
                now_ms=now_ms,
                hot=False,
            )
            self._log_result(
                started,
                response,
                mode="full",
                cache_status=cache_status,
            )
            return response

        full_sync_age_ms = max(0, now_ms - state.last_full_sync_ms)
        if full_sync_age_ms >= self.settings.thread_cache_full_sync_seconds * 1000:
            response = await self.client.get(sub_domain, board_dir, thread_id)
            cache_status = await self._store_full_response(
                cache_url,
                response,
                now_ms=now_ms,
                hot=True,
                delete_if_ineligible=True,
            )
            self._log_result(
                started,
                response,
                mode="full_reconcile",
                cache_status=cache_status,
                full_sync_age_ms=full_sync_age_ms,
            )
            return response

        last_reply_no = state.last_reply_no
        if last_reply_no is None:
            return await self._fallback_to_full(
                cache_url,
                sub_domain,
                board_dir,
                thread_id,
                now_ms,
                started,
                reason="invalid_cached_last_reply",
            )

        incremental = await self.client.get_incremental(
            sub_domain,
            board_dir,
            thread_id,
            last_reply_no + 1,
        )
        if incremental.status_code != 200 or incremental.data is None:
            return await self._fallback_to_full(
                cache_url,
                sub_domain,
                board_dir,
                thread_id,
                now_ms,
                started,
                reason=f"incremental_status_{incremental.status_code}",
            )

        try:
            merged_thread, new_replies = merge_incremental_thread(
                state.thread, incremental.data
            )
        except ValueError:
            return await self._fallback_to_full(
                cache_url,
                sub_domain,
                board_dir,
                thread_id,
                now_ms,
                started,
                reason="invalid_incremental_response",
            )

        hot_state = CachedThreadState(
            opener=state.opener,
            thread=merged_thread,
            last_full_sync_ms=state.last_full_sync_ms,
            hot=True,
        )
        await self.store.put(
            cache_url,
            hot_state,
            self.settings.thread_cache_hot_ttl_seconds,
        )
        response = ThreadJsonResponse(
            status_code=200,
            opener=hot_state.opener,
            thread=hot_state.thread,
        )
        self._log_result(
            started,
            response,
            mode="incremental",
            cache_status="hot",
            new_replies=new_replies,
            full_sync_age_ms=full_sync_age_ms,
        )
        return response

    async def _fallback_to_full(
        self,
        cache_url: str,
        sub_domain: str,
        board_dir: str,
        thread_id: str | int,
        now_ms: int,
        started: float,
        *,
        reason: str,
    ) -> ThreadJsonResponse:
        response = await self.client.get(sub_domain, board_dir, thread_id)
        cache_status = await self._store_full_response(
            cache_url,
            response,
            now_ms=now_ms,
            hot=True,
            delete_if_ineligible=True,
        )
        self._log_result(
            started,
            response,
            mode="full_fallback",
            cache_status=cache_status,
            fallback_reason=reason,
        )
        return response

    async def _store_full_response(
        self,
        cache_url: str,
        response: ThreadJsonResponse,
        *,
        now_ms: int,
        hot: bool,
        delete_if_ineligible: bool = False,
    ) -> str:
        if (
            response.status_code != 200
            or response.opener is None
            or response.thread is None
        ):
            if delete_if_ineligible:
                await self.store.delete(cache_url)
            return "not_stored"

        replies = response.thread.get("res")
        reply_count = len(replies) if isinstance(replies, dict) else 0
        if reply_count < self.settings.thread_cache_min_replies:
            if delete_if_ineligible:
                await self.store.delete(cache_url)
            return "below_threshold"

        state = CachedThreadState(
            opener=response.opener,
            thread=response.thread,
            last_full_sync_ms=now_ms,
            hot=hot,
        )
        ttl_seconds = (
            self.settings.thread_cache_hot_ttl_seconds
            if hot
            else self.settings.thread_cache_candidate_ttl_seconds
        )
        await self.store.put(cache_url, state, ttl_seconds)
        return "hot" if hot else "candidate"

    @staticmethod
    def _log_result(
        started: float,
        response: ThreadJsonResponse,
        *,
        mode: str,
        cache_status: str,
        new_replies: int = 0,
        **fields: Any,
    ) -> None:
        replies = response.thread.get("res") if response.thread else None
        log_event(
            "thread_fetch_completed",
            status=response.status_code,
            mode=mode,
            cache_status=cache_status,
            reply_count=len(replies) if isinstance(replies, dict) else 0,
            new_replies=new_replies,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            **fields,
        )
