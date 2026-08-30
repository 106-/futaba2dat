import time
from urllib.parse import urlparse

import asgi
from workers import WorkerEntrypoint

from main import app
from telemetry import log_event


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        started = time.perf_counter()
        method = str(request.method)
        path = urlparse(str(request.url)).path

        try:
            response = await asgi.fetch(app, request, self.env)
        except Exception as exc:
            log_event(
                "worker_request_failed",
                level="error",
                method=method,
                path=path,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        log_event(
            "worker_request_completed",
            method=method,
            path=path,
            status=int(response.status),
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return response
