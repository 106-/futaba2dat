"""
URL変換機能のテスト
"""

from futaba2dat.transform import convert_futaba_urls_to_2ch_format


def test_convert_futaba_urls_to_2ch_format():
    """ふたばちゃんねるURLを2ch形式URLに変換するテスト"""
    
    # テスト用のスレッドデータ
    test_thread = {
        "posts": [
            {
                "body": "これは普通の投稿です"
            },
            {
                "body": "http://may.2chan.net/b/res/12345.htm<br>このスレッド見て"
            },
            {
                "body": "https://dec.2chan.net/58/res/67890.htm<br>転載不可板のスレ"
            },
            {
                "body": "複数URL<br>http://img.2chan.net/b/res/11111.htm<br>と<br>https://jun.2chan.net/jun/res/22222.htm"
            },
            {
                "body": "ふたば以外のURL http://example.com/test.htm は変換されない"
            }
        ]
    }
    
    # プロキシドメイン
    proxy_domain = "myproxy.example.com"
    
    # URL変換実行
    result_thread = convert_futaba_urls_to_2ch_format(test_thread, proxy_domain)
    
    # 期待される変換結果をチェック
    expected_conversions = [
        ("http://may.2chan.net/b/res/12345.htm", "http://myproxy.example.com/test/read.cgi/may/b/12345/"),
        ("https://dec.2chan.net/58/res/67890.htm", "http://myproxy.example.com/test/read.cgi/dec/58/67890/"),
        ("http://img.2chan.net/b/res/11111.htm", "http://myproxy.example.com/test/read.cgi/img/b/11111/"),
        ("https://jun.2chan.net/jun/res/22222.htm", "http://myproxy.example.com/test/read.cgi/jun/jun/22222/")
    ]
    
    # 変換確認
    for original, expected in expected_conversions:
        found = False
        for post in result_thread["posts"]:
            if expected in post["body"] and original not in post["body"]:
                found = True
                break
        assert found, f"変換失敗: {original} -> {expected}"
    
    # ふたば以外のURLが変換されていないことを確認
    non_futaba_preserved = False
    for post in result_thread["posts"]:
        if "http://example.com/test.htm" in post["body"]:
            non_futaba_preserved = True
            break
    
    assert non_futaba_preserved, "ふたば以外のURLが意図せず変換された"


def test_convert_futaba_urls_empty_posts():
    """空のpostsリストでの変換テスト"""
    test_thread = {"posts": []}
    proxy_domain = "example.com"
    
    result = convert_futaba_urls_to_2ch_format(test_thread, proxy_domain)
    assert result["posts"] == []


def test_convert_futaba_urls_no_urls():
    """ふたばURLが含まれない投稿での変換テスト"""
    test_thread = {
        "posts": [
            {"body": "普通のテキスト"},
            {"body": "他のサイトのURL http://example.com"},
        ]
    }
    proxy_domain = "example.com"
    
    result = convert_futaba_urls_to_2ch_format(test_thread, proxy_domain)
    
    assert result["posts"][0]["body"] == "普通のテキスト"
    assert result["posts"][1]["body"] == "他のサイトのURL http://example.com"