futaba2dat
===

ふたば☆ちゃんねるのスレッドを5chのdat形式に変換するプログラム

## このプログラムは?

このプログラムは, ふたば☆ちゃんねるのスレッドを読み込み5chなどで使われているdat形式に変換するものです. 今のところChMateでの使用を推定しています.

## 使い方

### ChMateから使う

現在[die-or.work](http://die-or.work)で試験的に動かしているのでそのまま使えます.
例えばChMateの `設定メニュー -> URLを指定して開く` に `http://die-or.work/may/b/` を入力して開くとmay板のスレッド一覧が表示されます.

### Dockerで動かす

ローカルで直に動かすためにはpoetryのインストールが必要となるため若干面倒くさいです.
そこでここでにはDockerを使用した方法を載せておきます.

1. リポジトリをローカルにcloneする
```
$ git clone git@github.com:106-/futaba2dat.git
$ cd futaba2dat
```

2. Dockerコンテナをbuildする
```
$ make build
```

3. Dockerコンテナを起動する
```
$ docker run -d -p 80:80 futaba2dat
```