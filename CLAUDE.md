# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

- あなたはコーディングが得意なずんだの妖精です。
- あなたは日本語で話し、文末に「〜のだ。」「〜なのだ。」をつけます。

## プロジェクト概要

**futaba2dat** は、ふたば☆ちゃんねるのスレッドを5ch/2chのDAT形式に変換するFastAPI Webアプリケーションです。ChMateなどのモバイル2chブラウザからふたばちゃんねるを閲覧できるようにするプロキシサーバーとして動作します。

## アーキテクチャ

### 主要コンポーネント

- **FastAPIアプリケーション** (`src/main.py`): 2ch形式のエンドポイントを提供するメインWebサーバー
- **ふたばスクレイパー** (`src/futaba.py`): `FutabaBoard`と`FutabaThread`クラスによる板カタログとスレッド内容の取得
- **変換レイヤー** (`src/transform.py`): URL変換とコンテンツ変換、リバースプロキシURL書き換え機能
- **データベースレイヤー** (`src/db.py`): Cloudflare D1ベースの閲覧履歴管理
- **Workersエントリポイント** (`src/worker.py`): FastAPIをCloudflare Workersへ接続

### リクエストフロー

1. クライアントが2ch形式URL（例：`/may/b/`や`/may/b/dat/12345.dat`）でリクエスト
2. 対応するふたばURLをpyfetch + BeautifulSoupでスクレイピング
3. Jinja2テンプレートを使用してDAT形式に変換
4. コンテンツ内のURLをプロキシドメインに書き換え
5. Shift-JISエンコードしてレスポンス返却

### 重要な機能

- **URL書き換え**: Workersが受信した`Host`からプロキシドメインを取得し、ふたばURLをプロキシURLに書き換え
- **データベースインデックス**: `created_at`カラムにインデックスを設定し、履歴クエリを高速化
- **板管理**: `tools/make_boards.py`による動的な板リスト生成

## 開発コマンド

### 日常開発
```bash
# ローカルWorkers起動（ホットリロード対応）
make run

# テスト実行
make test                          # pytestで全テスト実行
uv run pytest tests/test_app.py -v          # ローカルWorker統合テストのみ
uv run pytest tests/test_url_conversion.py  # URL変換テストのみ

# コード品質
make lint                          # コードスタイルチェック
make format                        # フォーマット自動修正

# ふたばから板リスト更新
make reload-boards
```

## テスト戦略

- **単体テスト**: `test_futaba.py`（パース処理）、`test_url_conversion.py`（変換関数）
- **統合テスト**: `test_app.py`（pywrangler dev上のエンドポイント。TestClientや通常Python用フォールバックは使用しない）
テストはローカルWorkerを起動し、HTTP経由で検証する。

## 設定

D1 binding名は`DB`。履歴保存は`HISTORY_WRITES`で制御する。

`src/templates/`ディレクトリのテンプレートが2ch互換形式を生成：
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

## ClaudeCodeActionでの実行について

ClaudeCodeActionでは以下のように `allowed_tools` が設定されています。ここにあるコマンド以外を実行しようとしないでください。
```
allowed_tools: "Bash(uv:*),Bash(make format),Bash(make lint),Bash(make test),Bash(make build)"
```

## 重要な注意点

- 日本語テキストエンコーディング前提（Shift-JIS出力）
- `src/boards.json`の板定義は手動更新またはスクリプト再生成が必要
- URL書き換えは`*.2chan.net/*/res/*.htm`パターンを`/test/read.cgi/`形式に変換する仕様
