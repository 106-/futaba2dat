import time
from dataclasses import dataclass
from typing import Any

from telemetry import log_event


@dataclass(slots=True)
class History:
    """DAT の閲覧履歴。created_at は Unix epoch milliseconds。"""

    title: str
    link: str
    board: str
    host: str
    created_at: int
    id: int | None = None


def _rows(result: Any) -> list[Any]:
    return list(result.results)


def _count(result: Any, name: str) -> int:
    rows = _rows(result)
    return int(rows[0][name]) if rows else 0


def _result_metrics(result: Any) -> dict[str, int | float]:
    meta = getattr(result, "meta", None)
    if meta is None:
        return {}

    metrics: dict[str, int | float] = {}
    for name, cast in (
        ("duration", float),
        ("rows_read", int),
        ("rows_written", int),
    ):
        value = getattr(meta, name, None)
        if value is not None:
            metrics[name] = cast(value)
    return metrics


def _log_d1_result(operation: str, started: float, results: list[Any]) -> None:
    result_metrics = [_result_metrics(result) for result in results]
    log_event(
        "d1_query_completed",
        operation=operation,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        sql_duration_ms=round(
            sum(float(metrics.get("duration", 0)) for metrics in result_metrics),
            2,
        ),
        rows_read=sum(int(metrics.get("rows_read", 0)) for metrics in result_metrics),
        rows_written=sum(
            int(metrics.get("rows_written", 0)) for metrics in result_metrics
        ),
    )


def _log_d1_error(operation: str, started: float, exc: Exception) -> None:
    log_event(
        "d1_query_failed",
        level="error",
        operation=operation,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        error_type=type(exc).__name__,
        error=str(exc),
    )


class D1HistoryRepository:
    """Cloudflare D1 binding を利用する履歴リポジトリ。"""

    def __init__(self, database: Any):
        self.database = database

    async def add(self, history: History) -> None:
        started = time.perf_counter()
        statement = self.database.prepare(
            """
            INSERT INTO histories (title, link, board, host, created_at)
            VALUES (?1, ?2, ?3, ?4, ?5)
            """
        ).bind(
            history.title,
            history.link,
            history.board,
            history.host,
            history.created_at,
        )
        try:
            result = await statement.run()
        except Exception as exc:
            _log_d1_error("history_add", started, exc)
            raise
        _log_d1_result("history_add", started, [result])

    async def get_recent(self, limit: int = 50) -> list[History]:
        started = time.perf_counter()
        try:
            result = (
                await self.database.prepare(
                    """
                SELECT id, title, link, board, host, created_at
                FROM histories
                ORDER BY created_at DESC, id DESC
                LIMIT ?1
                """
                )
                .bind(limit)
                .run()
            )
        except Exception as exc:
            _log_d1_error("history_recent", started, exc)
            raise
        _log_d1_result("history_recent", started, [result])
        return [
            History(
                id=int(row["id"]),
                title=str(row["title"]),
                link=str(row["link"]),
                board=str(row["board"]),
                host=str(row["host"]),
                created_at=int(row["created_at"]),
            )
            for row in _rows(result)
        ]

    async def get_dashboard_analytics(self) -> dict[str, Any]:
        started = time.perf_counter()
        now_ms = int(time.time() * 1000)
        day_ago = now_ms - 24 * 60 * 60 * 1000
        week_ago = now_ms - 7 * 24 * 60 * 60 * 1000
        statements = [
            self.database.prepare(
                """SELECT board, COUNT(*) AS access_count FROM histories
                WHERE created_at > ?1 GROUP BY board
                ORDER BY access_count DESC LIMIT 10"""
            ).bind(day_ago),
            self.database.prepare(
                """SELECT board, COUNT(*) AS access_count FROM histories
                WHERE created_at > ?1 GROUP BY board
                ORDER BY access_count DESC LIMIT 10"""
            ).bind(week_ago),
            self.database.prepare(
                """SELECT title, link, board, COUNT(*) AS access_count
                FROM histories WHERE created_at > ?1
                GROUP BY title, link, board
                ORDER BY access_count DESC LIMIT 10"""
            ).bind(day_ago),
            self.database.prepare(
                """SELECT title, link, board, COUNT(*) AS access_count
                FROM histories WHERE created_at > ?1
                GROUP BY title, link, board
                ORDER BY access_count DESC LIMIT 10"""
            ).bind(week_ago),
            self.database.prepare(
                "SELECT COUNT(DISTINCT host) AS value FROM histories WHERE created_at > ?1"
            ).bind(day_ago),
            self.database.prepare(
                "SELECT COUNT(DISTINCT host) AS value FROM histories WHERE created_at > ?1"
            ).bind(week_ago),
            self.database.prepare(
                "SELECT COUNT(*) AS value FROM histories WHERE created_at > ?1"
            ).bind(day_ago),
            self.database.prepare(
                "SELECT COUNT(*) AS value FROM histories WHERE created_at > ?1"
            ).bind(week_ago),
        ]
        try:
            results = list(await self.database.batch(statements))
        except Exception as exc:
            _log_d1_error("history_analytics", started, exc)
            raise
        _log_d1_result("history_analytics", started, results)

        def ranking(result: Any, fields: tuple[str, ...]) -> list[dict[str, Any]]:
            return [{field: row[field] for field in fields} for row in _rows(result)]

        return {
            "board_popularity_day": ranking(results[0], ("board", "access_count")),
            "board_popularity": ranking(results[1], ("board", "access_count")),
            "thread_popularity_day": ranking(
                results[2], ("title", "link", "board", "access_count")
            ),
            "thread_popularity": ranking(
                results[3], ("title", "link", "board", "access_count")
            ),
            "unique_users_day": _count(results[4], "value"),
            "unique_users_week": _count(results[5], "value"),
            "total_access_day": _count(results[6], "value"),
            "total_access_week": _count(results[7], "value"),
        }
