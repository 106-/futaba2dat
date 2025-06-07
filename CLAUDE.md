# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

**futaba2dat** は、ふたば☆ちゃんねるのスレッドを5ch/2chのDAT形式に変換するFastAPI Webアプリケーションです。ChMateなどのモバイル2chブラウザからふたばちゃんねるを閲覧できるようにするプロキシサーバーとして動作します。

## アーキテクチャ

### 主要コンポーネント

- **FastAPIアプリケーション** (`futaba2dat/main.py`): 2ch形式のエンドポイントを提供するメインWebサーバー
- **ふたばスクレイパー** (`futaba2dat/futaba.py`): `FutabaBoard`と`FutabaThread`クラスによる板カタログとスレッド内容の取得
- **変換レイヤー** (`futaba2dat/transform.py`): URL変換とコンテンツ変換、リバースプロキシURL書き換え機能
- **データベースレイヤー** (`futaba2dat/db.py`): SQLAlchemyベースの閲覧履歴管理、インデックス最適化済み
- **設定管理** (`futaba2dat/settings.py`): Pydanticベースの設定管理

### リクエストフロー

1. クライアントが2ch形式URL（例：`/may/b/`や`/may/b/dat/12345.dat`）でリクエスト
2. 対応するふたばURLをrequests + BeautifulSoupでスクレイピング
3. Jinja2テンプレートを使用してDAT形式に変換
4. コンテンツ内のURLをプロキシドメインに書き換え
5. Shift-JISエンコードしてレスポンス返却

### 重要な機能

- **リバースプロキシ対応**: `X-Forwarded-Host`ヘッダーからプロキシドメインを自動検出し、ふたばURLをプロキシURLに書き換え
- **データベースインデックス**: `created_at`カラムにインデックスを設定し、履歴クエリを高速化
- **板管理**: `tools/make_boards.py`による動的な板リスト生成

## 開発コマンド

### 日常開発
```bash
# 開発サーバー起動（ホットリロード対応）
make run                           # ポート8001で起動

# テスト実行
make test                          # pytestで全テスト実行
poetry run pytest tests/test_app.py -v          # アプリ統合テストのみ
poetry run pytest tests/test_url_conversion.py  # URL変換テストのみ

# コード品質
make lint                          # コードスタイルチェック
make format                        # フォーマット自動修正

# ふたばから板リスト更新
make reload-boards
```

### Docker操作
```bash
make build                         # Dockerイメージビルド
make docker-run                    # コンテナ起動
make clean                         # コンテナ・イメージ削除
```

## テスト戦略

- **単体テスト**: `test_futaba.py`（パース処理）、`test_url_conversion.py`（変換関数）
- **統合テスト**: `test_app.py`（FastAPIエンドポイント全体、TestClient使用）
- **データベーステスト**: `test_db_index.py`（スキーマとインデックス検証）

テストフィクスチャはインメモリSQLiteを使用し、外部ふたばリクエストはモック化。

## 設定

データベース設定は環境変数で可能だが、デフォルトはSQLite（`log.sqlite`）。データベース接続は起動時に`Settings`クラスで設定。

`templates/`ディレクトリのテンプレートが2ch互換形式を生成：
- `thread.j2`: DAT形式スレッド内容
- `subject.j2`: スレッド一覧  
- `bbsmenu.j2`: 板メニュー

## 開発ワークフロー

**重要**: コードに変更を加えた後は、必ず以下のコマンドを順番に実行してください：

```bash
make format    # コードフォーマット自動修正
make lint      # コードスタイルチェック
make test      # 全テスト実行
```

これにより、コード品質とテストの整合性が保たれます。

## 重要な注意点

- ふたばへの外部HTTPリクエストは全て同期処理（非同期化によるリファクタリング余地あり）
- 日本語テキストエンコーディング前提（Shift-JIS出力）
- `futaba2dat/boards.json`の板定義は手動更新またはスクリプト再生成が必要
- URL書き換えは`*.2chan.net/*/res/*.htm`パターンを`/test/read.cgi/`形式に変換する仕様