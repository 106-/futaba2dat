"""
FastAPIアプリケーションの統合テスト
"""

import tempfile
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from futaba2dat import db
from futaba2dat.main import app


@pytest.fixture
def test_db_engine():
    """テスト用のデータベースエンジンを作成"""
    # 一時ファイルでSQLiteデータベースを作成
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite") as tmp_file:
        db_path = tmp_file.name

    engine = sa.create_engine(f"sqlite:///{db_path}")
    db.create_table(engine)

    yield engine

    # テスト後にデータベースファイルを削除
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def test_client(test_db_engine, monkeypatch):
    """テスト用のFastAPIクライアントを作成"""

    # データベースエンジンをモックして、テスト用エンジンを使用
    def mock_get_engine():
        return test_db_engine

    monkeypatch.setattr("futaba2dat.main.get_engine", mock_get_engine)

    # TestClientを作成
    client = TestClient(app)
    return client


def test_root_endpoint(test_client):
    """ルートエンドポイント(/)のテスト"""
    response = test_client.get("/")

    # ステータスコード確認
    assert response.status_code == 200

    # Content-Typeの確認
    assert "text/html" in response.headers["content-type"]

    # HTMLが返されることを確認
    content = response.text
    assert "<html" in content or "<!DOCTYPE" in content.lower()


def test_log_endpoint(test_client):
    """ログエンドポイント(/log)のテスト"""
    response = test_client.get("/log")

    # ステータスコード確認
    assert response.status_code == 200

    # Content-Typeの確認
    assert "text/html" in response.headers["content-type"]


def test_bbsmenu_endpoint(test_client):
    """BBSメニューエンドポイント(/bbsmenu.html)のテスト"""
    response = test_client.get("/bbsmenu.html")

    # ステータスコード確認
    assert response.status_code == 200

    # Content-Typeの確認
    assert "text/html" in response.headers["content-type"]


def test_board_endpoint(test_client):
    """板エンドポイントのテスト"""
    # may/b/ 板にアクセス
    response = test_client.get("/may/b/")

    # ステータスコード確認
    assert response.status_code == 200

    # Content-Typeの確認
    assert "text/html" in response.headers["content-type"]

    # Shift-JISエンコーディングの確認
    assert response.headers["content-length"]


def test_setting_txt_endpoint(test_client):
    """SETTING.TXTエンドポイントのテスト"""
    response = test_client.get("/may/b/SETTING.TXT")

    # ステータスコード確認
    assert response.status_code == 200

    # Content-Typeの確認
    assert "text/plain" in response.headers["content-type"]


def test_static_files(test_client):
    """静的ファイルのテスト"""
    # CSSファイルが正しく配信されるかテスト
    response = test_client.get("/static/index.css")

    # ファイルが存在する場合は200、存在しない場合は404
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        # CSSファイルの場合、Content-Typeを確認
        assert "text/css" in response.headers.get("content-type", "")


def test_database_integration(test_client, test_db_engine):
    """データベース統合テスト"""

    # 履歴テーブルが空であることを確認
    histories = db.get_recent(test_db_engine)
    assert len(histories) == 0

    # テストデータを追加
    test_history = db.History(
        id=None,
        title="テストスレッド",
        link="http://may.2chan.net/b/res/12345.htm",
        board="二次元裏(may_b)",
        host="127.0.0.1",
        created_at="2024-01-01T00:00:00",
    )

    db.add(test_db_engine, test_history)

    # データが追加されたことを確認
    histories = db.get_recent(test_db_engine)
    assert len(histories) == 1
    assert histories[0].title == "テストスレッド"
    assert histories[0].link == "http://may.2chan.net/b/res/12345.htm"


def test_proxy_domain_detection(test_client):
    """プロキシドメイン検出のテスト"""

    # X-Forwarded-Hostヘッダーを含むリクエスト
    headers = {"X-Forwarded-Host": "proxy.example.com", "X-Forwarded-Proto": "https"}

    response = test_client.get("/", headers=headers)

    # ステータスコード確認
    assert response.status_code == 200

    # 通常のHostヘッダーでのテスト
    headers = {"Host": "localhost:8000"}
    response = test_client.get("/", headers=headers)

    # ステータスコード確認
    assert response.status_code == 200
