from copy import deepcopy

import pytest

from futaba import ThreadJsonResponse, UpstreamJsonResponse
from thread_cache import (
    CachedThreadState,
    ThreadCacheCoordinator,
    build_thread_cache_url,
    merge_incremental_thread,
)


def _thread_data(reply_count: int, *, die: str = "12:00") -> dict:
    return {
        "die": die,
        "sd": {},
        "res": {
            str(1000 + index): {"com": f"reply {index}"} for index in range(reply_count)
        },
    }


def _full_response(reply_count: int) -> ThreadJsonResponse:
    return ThreadJsonResponse(
        status_code=200,
        opener={"res": {"999": {"com": "opener"}}},
        thread=_thread_data(reply_count),
    )


class _MemoryStore:
    def __init__(self, state: CachedThreadState | None = None):
        self.state = state
        self.puts = []
        self.deletes = []

    async def get(self, _cache_url):
        return self.state

    async def put(self, cache_url, state, ttl_seconds):
        self.state = state
        self.puts.append((cache_url, state, ttl_seconds))

    async def delete(self, cache_url):
        self.state = None
        self.deletes.append(cache_url)


class _FakeThreadClient:
    def __init__(
        self,
        full_response: ThreadJsonResponse,
        incremental_response: UpstreamJsonResponse | None = None,
    ):
        self.full_response = full_response
        self.incremental_response = incremental_response
        self.full_calls = []
        self.incremental_calls = []

    async def get(self, sub_domain, board_dir, thread_id):
        self.full_calls.append((sub_domain, board_dir, thread_id))
        return deepcopy(self.full_response)

    async def get_incremental(self, sub_domain, board_dir, thread_id, start_post_no):
        self.incremental_calls.append((sub_domain, board_dir, thread_id, start_post_no))
        assert self.incremental_response is not None
        return deepcopy(self.incremental_response)


@pytest.mark.asyncio
async def test_first_large_thread_is_stored_as_candidate():
    store = _MemoryStore()
    client = _FakeThreadClient(_full_response(100))
    coordinator = ThreadCacheCoordinator(
        store,
        client=client,
        clock_ms=lambda: 1_000_000,
    )

    response = await coordinator.get(
        "https://test.die-or.work/may/b/dat/999.dat", "may", "b", 999
    )

    assert response.status_code == 200
    assert len(client.full_calls) == 1
    assert client.incremental_calls == []
    assert len(store.puts) == 1
    assert store.puts[0][1].hot is False
    assert store.puts[0][1].reply_count == 100
    assert store.puts[0][2] == 300


@pytest.mark.asyncio
async def test_small_thread_is_not_cached():
    store = _MemoryStore()
    client = _FakeThreadClient(_full_response(99))
    coordinator = ThreadCacheCoordinator(
        store,
        client=client,
        clock_ms=lambda: 1_000_000,
    )

    await coordinator.get("https://test.die-or.work/may/b/dat/999.dat", "may", "b", 999)

    assert store.puts == []


@pytest.mark.asyncio
async def test_candidate_hit_uses_incremental_fetch_and_becomes_hot():
    cached_thread = _thread_data(100)
    cached_thread["sd"] = {"1000": "1"}
    state = CachedThreadState(
        opener={"res": {"999": {"com": "opener"}}},
        thread=cached_thread,
        last_full_sync_ms=1_000_000,
        hot=False,
    )
    incremental = UpstreamJsonResponse(
        200,
        {
            "die": "12:05",
            "sd": {"1000": "2", "1099": "3"},
            "res": {"1100": {"com": "new reply"}},
        },
    )
    store = _MemoryStore(state)
    client = _FakeThreadClient(_full_response(101), incremental)
    coordinator = ThreadCacheCoordinator(
        store,
        client=client,
        clock_ms=lambda: 1_100_000,
    )

    response = await coordinator.get(
        "https://test.die-or.work/may/b/dat/999.dat", "may", "b", 999
    )

    assert client.full_calls == []
    assert client.incremental_calls == [("may", "b", 999, 1100)]
    assert response.thread is not None
    assert len(response.thread["res"]) == 101
    assert response.thread["sd"] == {"1000": "2", "1099": "3"}
    assert response.thread["die"] == "12:05"
    assert store.puts[-1][1].hot is True
    assert store.puts[-1][1].last_full_sync_ms == 1_000_000
    assert store.puts[-1][2] == 3600


@pytest.mark.asyncio
async def test_hot_thread_is_fully_reconciled_after_five_minutes():
    state = CachedThreadState(
        opener={"res": {"999": {"com": "opener"}}},
        thread=_thread_data(100),
        last_full_sync_ms=1_000_000,
        hot=True,
    )
    store = _MemoryStore(state)
    client = _FakeThreadClient(_full_response(101))
    coordinator = ThreadCacheCoordinator(
        store,
        client=client,
        clock_ms=lambda: 1_300_000,
    )

    response = await coordinator.get(
        "https://test.die-or.work/may/b/dat/999.dat", "may", "b", 999
    )

    assert response.thread is not None
    assert len(response.thread["res"]) == 101
    assert len(client.full_calls) == 1
    assert client.incremental_calls == []
    assert store.puts[-1][1].hot is True
    assert store.puts[-1][1].last_full_sync_ms == 1_300_000
    assert store.puts[-1][2] == 3600


@pytest.mark.asyncio
async def test_invalid_incremental_response_falls_back_to_full_fetch():
    state = CachedThreadState(
        opener={"res": {"999": {"com": "opener"}}},
        thread=_thread_data(100),
        last_full_sync_ms=1_000_000,
        hot=True,
    )
    store = _MemoryStore(state)
    client = _FakeThreadClient(
        _full_response(101),
        UpstreamJsonResponse(200, {"sd": {}, "res": {}}),
    )
    coordinator = ThreadCacheCoordinator(
        store,
        client=client,
        clock_ms=lambda: 1_100_000,
    )

    response = await coordinator.get(
        "https://test.die-or.work/may/b/dat/999.dat", "may", "b", 999
    )

    assert response.thread is not None
    assert len(response.thread["res"]) == 101
    assert len(client.incremental_calls) == 1
    assert len(client.full_calls) == 1
    assert store.puts[-1][1].hot is True


def test_cached_state_json_round_trip():
    state = CachedThreadState(
        opener={"res": {"999": {"com": "本文"}}},
        thread=_thread_data(100),
        last_full_sync_ms=123456,
        hot=True,
    )

    restored = CachedThreadState.from_json(state.to_json())

    assert restored == state
    assert restored.reply_count == 100
    assert restored.last_reply_no == 1099


def test_merge_incremental_replaces_metadata_and_appends_replies():
    cached = _thread_data(2, die="12:00")
    cached["sd"] = {"1000": "1"}
    merged, new_replies = merge_incremental_thread(
        cached,
        {
            "die": "12:05",
            "sd": {"1001": "2"},
            "res": {"1002": {"com": "new"}},
        },
    )

    assert len(merged["res"]) == 3
    assert merged["sd"] == {"1001": "2"}
    assert merged["die"] == "12:05"
    assert new_replies == 1


def test_merge_incremental_requires_current_sodane_values():
    with pytest.raises(ValueError, match="sodane"):
        merge_incremental_thread(
            _thread_data(2),
            {"die": "12:05", "res": {"1002": {"com": "new"}}},
        )


def test_thread_cache_url_is_scoped_to_request_origin():
    assert build_thread_cache_url(
        "https://test.die-or.work/may/b/dat/999.dat",
        "may",
        "b",
        999,
    ) == ("https://test.die-or.work/.futaba2dat-cache/thread-state/v1/may/b/999")
