futaba2dat
===

ふたば☆ちゃんねるのスレッドを5chのdat形式に変換するプログラム

## このプログラムは?

このプログラムは, ふたば☆ちゃんねるのスレッドを読み込み5chなどで使われているdat形式に変換するものです. 今のところChMateでの使用を想定しています.

## 使い方

### ChMateから使う

現在[die-or.work](http://die-or.work)で試験的に動かしているのでそのまま使えます.
例えばChMateの `設定メニュー -> URLを指定して開く` に `http://die-or.work/may/b/` を入力して開くとmay板のスレッド一覧が表示されます.

### Dockerで動かす

[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-ubiq%2Ffutaba2dat-blue?logo=docker)](https://hub.docker.com/r/ubiq/futaba2dat) 

ローカルで直に動かすためにはpoetryのインストールが必要となるため若干面倒くさいです.

dockerhubに最新版があるので、それを使うのが一番楽です。
```
$ docker run -d -p 80:80 ubiq/futaba2dat:latest
```