import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

PROJECT_ROOT = Path(__file__).parent


@dataclass(frozen=True, slots=True)
class WorkerResponse:
    status_code: int
    headers: Message
    content: bytes


class WorkerClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get(self, path: str) -> WorkerResponse:
        try:
            opened = urlopen(f"{self.base_url}{path}", timeout=30)
        except HTTPError as error:
            opened = error
        with opened as response:
            return WorkerResponse(
                status_code=response.status,
                headers=response.headers,
                content=response.read(),
            )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def worker_client():
    """pywrangler dev の実ランタイムへHTTPリクエストを送る。"""
    pywrangler = shutil.which("pywrangler")
    if pywrangler is None:
        raise RuntimeError("pywrangler is required to run the Worker tests")

    port = _free_port()
    log = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
    process = subprocess.Popen(
        [pywrangler, "dev", "--port", str(port)],
        cwd=PROJECT_ROOT,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=True,
    )
    client = WorkerClient(f"http://127.0.0.1:{port}")

    try:
        for _ in range(120):
            if process.poll() is not None:
                break
            try:
                if client.get("/").status_code == 200:
                    yield client
                    return
            except URLError:
                pass
            time.sleep(0.5)

        log.seek(0)
        raise RuntimeError(f"Worker did not start:\n{log.read()}")
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        log.close()
