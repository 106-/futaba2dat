"""
実際のふたば☆ちゃんねるを使った統合テスト

これらのテストは外部依存があるため、明示的に実行する必要があります：
pytest -m integration

注意: これらのテストは実際のふたばサーバーに接続するため、
- ネットワーク接続が必要
- サーバーの応答時間に依存
- 実際のスレッドの存在に依存
"""

import pytest
from fastapi.testclient import TestClient

from futaba2dat.main import app

client = TestClient(app)


@pytest.mark.integration
def test_may_b_subject_txt():
    """may/bの実際のsubject.txtの取得テスト"""
    response = client.get("/may/b/subject.txt")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain"
    
    # レスポンスがShift-JISでエンコードされていることを確認
    content = response.content.decode("shift-jis")
    
    # subject.txtの形式確認：<thread_id>.dat<>スレッドタイトル (<post_count>)
    lines = content.strip().split("\n")
    assert len(lines) > 0
    
    # 最初の行の形式確認
    first_line = lines[0]
    assert ".dat<>" in first_line
    assert "(" in first_line and ")" in first_line
    
    # 最初のスレッドIDを返す（テスト関数は戻り値を持つべきではないのでコメントアウト）
    # return lines[0].split(".dat<>")[0]


@pytest.mark.integration
def test_may_b_thread_dat():
    """may/bの実際のスレッドDATファイルの取得テスト"""
    # まずsubject.txtから有効なスレッドIDを取得
    subject_response = client.get("/may/b/subject.txt")
    assert subject_response.status_code == 200
    
    content = subject_response.content.decode("shift-jis")
    lines = content.strip().split("\n")
    
    # 最初のスレッドのIDを取得
    first_line = lines[0]
    thread_id = first_line.split(".dat<>")[0]
    
    # そのスレッドのDATファイルを取得
    dat_response = client.get(f"/may/b/dat/{thread_id}.dat")
    
    assert dat_response.status_code == 200
    assert dat_response.headers["content-type"] == "text/plain"
    
    # レスポンスがShift-JISでエンコードされていることを確認
    dat_content = dat_response.content.decode("shift-jis")
    
    # DAT形式の確認：名前<>メール<>日付 ID<>本文<>スレッドタイトル
    dat_lines = dat_content.strip().split("\n")
    assert len(dat_lines) >= 1
    
    # 最初の行（スレ主の投稿）の形式確認
    first_post = dat_lines[0]
    parts = first_post.split("<>")
    assert len(parts) == 5  # 名前、メール、日付、本文、タイトル
    
    # 日付部分の確認（空の場合もあるので存在確認のみ）
    date_part = parts[2]
    # ふたばの日付形式は様々なので、文字列として存在することのみ確認
    assert isinstance(date_part, str)


@pytest.mark.integration
def test_board_top_page():
    """板トップページの取得テスト"""
    response = client.get("/may/b/")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html"
    
    # レスポンスがShift-JISでエンコードされていることを確認
    html_content = response.content.decode("shift-jis")
    
    # HTMLの基本構造確認（板トップページは簡素なのでtitleのみ確認）
    assert "<title>" in html_content
    
    # 板の名前が含まれていることを確認（may/bは「二次元裏@ふたば」）
    assert "二次元裏" in html_content


@pytest.mark.integration
def test_setting_txt():
    """SETTING.TXTファイルの取得テスト"""
    response = client.get("/may/b/SETTING.TXT")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain"
    
    # レスポンスがShift-JISでエンコードされていることを確認
    content = response.content.decode("shift-jis")
    
    # SETTING.TXTの基本形式確認
    lines = content.strip().split("\n")
    assert len(lines) > 0
    
    # 板の名前が含まれていることを確認
    assert "二次元裏" in content


@pytest.mark.integration
def test_full_workflow():
    """フルワークフローテスト：板一覧→スレッド一覧→スレッド内容"""
    
    # 1. 板トップページにアクセス
    board_response = client.get("/may/b/")
    assert board_response.status_code == 200
    
    # 2. スレッド一覧（subject.txt）を取得
    subject_response = client.get("/may/b/subject.txt")
    assert subject_response.status_code == 200
    
    content = subject_response.content.decode("shift-jis")
    lines = content.strip().split("\n")
    assert len(lines) > 0
    
    # 3. 最初のスレッドのDATファイルを取得
    first_line = lines[0]
    thread_id = first_line.split(".dat<>")[0]
    
    dat_response = client.get(f"/may/b/dat/{thread_id}.dat")
    assert dat_response.status_code == 200
    
    # 4. DATファイルの内容確認
    dat_content = dat_response.content.decode("shift-jis")
    dat_lines = dat_content.strip().split("\n")
    assert len(dat_lines) >= 1
    
    # 5. すべてのレスポンスが適切なcontent-typeを持っていることを確認
    assert board_response.headers["content-type"] == "text/html"
    assert subject_response.headers["content-type"] == "text/plain"
    assert dat_response.headers["content-type"] == "text/plain"


@pytest.mark.integration
def test_error_handling_404_thread():
    """存在しないスレッドの404ハンドリングテスト"""
    # 存在しないスレッドID（非常に大きな数値）でアクセス
    response = client.get("/may/b/dat/999999999.dat")
    
    # 404エラーでもFTBucketリンクを含む200レスポンスが返される
    assert response.status_code == 200
    
    content = response.content.decode("shift-jis")
    
    # 404メッセージの確認
    assert "スレッドが見つかりません" in content or "削除された" in content
    
    # FTBucketリンクが含まれていることを確認（may板の場合）
    assert "ftbucket.info" in content