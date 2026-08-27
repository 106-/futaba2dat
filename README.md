futaba2dat
===

ふたば☆ちゃんねるのスレッドを5chのdat形式に変換するプログラム

## このプログラムは?

ふたば☆ちゃんねるのスレッドを読み込み、5chなどで使われているdat形式に変換します。ChMateでの使用を想定しています。

## 使い方

### ChMateから使う

現在[die-or.work](http://die-or.work)で試験的に動かしているので、そのまま利用できます。

ChMateの`設定メニュー → URLを指定して開く`に`http://die-or.work/may/b/`を入力すると、may板のスレッド一覧が表示されます。

### ローカル環境で動かす

Python 3.13以上、[uv](https://docs.astral.sh/uv/)とNode.jsが必要です。

```bash
git clone https://github.com/106-/futaba2dat.git
cd futaba2dat
make run
```

ChMateから`http://localhost:8787/may/b/`を開くと動作確認できます。
