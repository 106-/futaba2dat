"""
FTBucket URL生成と404レスポンスのテスト
"""

import datetime
from unittest.mock import Mock, patch

import pytest

from futaba2dat.main import create_404_thread_response, generate_ftbucket_url

# test_app.pyからfixtureをインポート
from .test_app import test_client, test_db_engine


def test_generate_ftbucket_url_may():
    """may板のFTBucket URL生成テスト"""
    url = generate_ftbucket_url("may", "b", 12345)
    expected = "https://may.ftbucket.info/may/cont/may.2chan.net_b_res_12345/index.htm"
    assert url == expected


def test_generate_ftbucket_url_img():
    """img板のFTBucket URL生成テスト"""
    url = generate_ftbucket_url("img", "b", 67890)
    expected = "https://c3.ftbucket.info/img/cont/img.2chan.net_b_res_67890/index.htm"
    assert url == expected


def test_generate_ftbucket_url_jun():
    """jun板のFTBucket URL生成テスト"""
    url = generate_ftbucket_url("jun", "jun", 11111)
    expected = "https://c3.ftbucket.info/jun/cont/jun.2chan.net_jun_res_11111/index.htm"
    assert url == expected


def test_generate_ftbucket_url_other():
    """may/img/jun以外の板のFTBucket URL生成テスト"""
    url = generate_ftbucket_url("dec", "58", 99999)
    assert url is None


def test_create_404_thread_response_may():
    """may板の404レスポンス生成テスト"""
    thread = create_404_thread_response("may", "b", 12345)

    assert thread["title"] == "スレッドが見つかりません"
    assert thread["expire"] == "削除済み"
    assert len(thread["posts"]) == 1

    post = thread["posts"][0]
    assert post["name"] == "システム"
    assert post["no"] == "No.404"
    assert "may.ftbucket.info" in post["body"]
    assert "12345" in post["body"]


def test_create_404_thread_response_img():
    """img板の404レスポンス生成テスト"""
    thread = create_404_thread_response("img", "b", 67890)

    post = thread["posts"][0]
    assert "c3.ftbucket.info/img" in post["body"]
    assert "67890" in post["body"]


def test_create_404_thread_response_jun():
    """jun板の404レスポンス生成テスト"""
    thread = create_404_thread_response("jun", "jun", 11111)

    post = thread["posts"][0]
    assert "c3.ftbucket.info/jun" in post["body"]
    assert "11111" in post["body"]


def test_create_404_thread_response_other():
    """may/img/jun以外の板の404レスポンス生成テスト"""
    thread = create_404_thread_response("dec", "58", 99999)

    assert thread["title"] == "スレッドが見つかりません"
    post = thread["posts"][0]
    assert post["body"] == "このスレッドは削除されたか存在しません。"
    assert "ftbucket" not in post["body"]


def test_create_404_thread_response_date_format():
    """404レスポンスの日付フォーマットテスト"""
    with patch("futaba2dat.main.datetime") as mock_datetime:
        # 固定日時を設定
        mock_datetime.datetime.now.return_value = datetime.datetime(
            2024, 1, 1, 12, 30, 45
        )
        mock_datetime.datetime.strftime = datetime.datetime.strftime

        thread = create_404_thread_response("may", "b", 54321)
        post = thread["posts"][0]

        # 日付フォーマットが正しいことを確認
        assert "24/01/01" in post["date"]
        assert "12:30:45" in post["date"]


def test_404_thread_response_structure():
    """404レスポンスの構造テスト"""
    thread = create_404_thread_response("may", "b", 88888)

    # 必要なキーが存在することを確認
    required_keys = ["title", "expire", "posts"]
    for key in required_keys:
        assert key in thread

    # 投稿の構造確認
    post = thread["posts"][0]
    required_post_keys = [
        "title",
        "image",
        "name",
        "mail",
        "date",
        "id",
        "no",
        "sod",
        "body",
        "quote_res",
    ]
    for key in required_post_keys:
        assert key in post

    # 引用レスが空であることを確認
    assert post["quote_res"] == []


def test_404_no_history_logging(test_client, test_db_engine, monkeypatch):
    """404エラー時にログが記録されないことをテスト"""
    from unittest.mock import Mock

    from futaba2dat import db

    # データベースエンジンをモックして、テスト用エンジンを使用
    def mock_get_engine():
        return test_db_engine

    monkeypatch.setattr("futaba2dat.main.get_engine", mock_get_engine)

    # FutabaThread.getをモックして404を返すように設定
    mock_response = Mock()
    mock_response.status_code = 404

    async def mock_futaba_get(self, sub_domain, board_dir, thread_id):
        return mock_response

    monkeypatch.setattr("futaba2dat.futaba.FutabaThread.get", mock_futaba_get)

    # 404リクエストを送信
    response = test_client.get("/may/b/dat/12345.dat")

    # ステータスコードが200であることを確認
    # 本来は404を返すべきだが、FTBucketリンクを返したいため200を返す。
    assert response.status_code == 200

    # ログが記録されていないことを確認
    histories = db.get_recent(test_db_engine)
    assert len(histories) == 0
