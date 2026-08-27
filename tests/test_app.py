"""ローカル Cloudflare Workers 上でのエンドポイントテスト。"""

import pytest


def test_root_endpoint(worker_client):
    response = worker_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<html" in response.content or b"<!doctype" in response.content.lower()
    assert response.headers["cache-control"] == "no-store"


def test_bbsmenu_endpoint(worker_client):
    response = worker_client.get("/bbsmenu.html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_board_endpoint(worker_client):
    response = worker_client.get("/may/b/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html"
    response.content.decode("cp932")


def test_setting_txt_endpoint(worker_client):
    response = worker_client.get("/may/b/SETTING.TXT")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain"
    response.content.decode("cp932")


def test_static_files_use_assets_binding(worker_client):
    response = worker_client.get("/static/index.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert response.headers.get("cache-control") != "no-store"


@pytest.mark.parametrize(
    "path",
    [
        "/unknown/board/",
        "/unknown/board/SETTING.TXT",
        "/unknown/board/subject.txt",
        "/unknown/board/dat/1.dat",
    ],
)
def test_unknown_board_is_rejected_without_upstream_fetch(worker_client, path):
    response = worker_client.get(path)
    assert response.status_code == 404
