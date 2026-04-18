futaba2dat
===

ふたば☆ちゃんねるのスレッドを5chのdat形式に変換するプログラム

## このプログラムは?

このプログラムは, ふたば☆ちゃんねるのスレッドを読み込み5chなどで使われているdat形式に変換するものです. 今のところChMateでの使用を想定しています.

## 使い方

### ChMateから使う

現在[die-or.work](http://die-or.work)で試験的に動かしているのでそのまま使えます.
例えばChMateの `設定メニュー -> URLを指定して開く` に `http://die-or.work/may/b/` を入力して開くとmay板のスレッド一覧が表示されます.

### ローカル環境で動かす

[uv](https://docs.astral.sh/uv/) があれば依存関係のインストールから起動まで一発でできます。

```bash
# uvのインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# リポジトリのクローン
git clone https://github.com/106-/futaba2dat.git
cd futaba2dat

# 起動（依存関係のインストールも自動で行われます）
make run
```

デフォルトでポート80で起動します。利用中の専用ブラウザに `http://localhost/may/b/` を入力すると動作確認できます。

### Dockerで動かす

[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-ubiq%2Ffutaba2dat-blue?logo=docker)](https://hub.docker.com/r/ubiq/futaba2dat)

```bash
docker run -d -p 80:80 ubiq/futaba2dat:latest
```
