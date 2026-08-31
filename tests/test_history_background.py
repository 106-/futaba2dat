from unittest.mock import AsyncMock

import pytest

from db import History
from main import add_history_in_background


def history() -> History:
    return History(
        title="title",
        link="https://may.2chan.net/b/res/1.htm",
        board="二次元裏(may_b)",
        host="192.0.2.1",
        created_at=1,
    )


@pytest.mark.asyncio
async def test_add_history_in_background() -> None:
    repository = AsyncMock()
    item = history()

    await add_history_in_background(repository, item)

    repository.add.assert_awaited_once_with(item)


@pytest.mark.asyncio
async def test_add_history_in_background_does_not_propagate_failure(caplog) -> None:
    repository = AsyncMock()
    repository.add.side_effect = RuntimeError("D1 unavailable")

    await add_history_in_background(repository, history())

    assert "Background D1 history write failed" in caplog.text
