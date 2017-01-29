#!/usr/bin/python
# -*- coding:utf-8 -*-

from bs4 import BeautifulSoup
import re
import json
import urllib2

def main():
    res = urllib2.urlopen("http://may.2chan.net/b/res/461794640.htm").read().decode("cp932")
    thread = get_thread(res)
    print(json.dumps(thread, indent=2))

# スレッドを読みやすい形に変える
# html: スレッドのhtml
def get_thread(html):
    thread = {}
    thread['response'] = []
    bs = BeautifulSoup(html, "html.parser")

    # スレ立て人のレスポンスを抽出
    thre = bs.find("div", class_="thre")
    thread['response'].append(get_response(thre))
    
    # スレが消える時刻を取得
    thread['expire'] = thre.find("small", text=re.compile(u"\d{2}:\d{2}頃消えます")).string

    # スレ立て人の本文をスレッドタイトルとする
    thread['title'] = thre.find('blockquote').get_text(separator='<br>',strip=True)

    # 返信を抽出
    for i in thre.find_all("table", border="0"):
        thread['response'].append(get_response(i))
    
    return thread

# レスポンスの抽出
# i: レスポンスの部分を含むBeautifulSoupのTag
def get_response(i):
    resp = {}
    
    title = i.find("font", color="#cc1105")
    if(title):
        resp['title'] = title.string
    else:
        resp['title'] = ""
  
    resp['body'] = i.find('blockquote').get_text(separator='<br>',strip=True)

    # メールアドレスを書いているひとだったら
    name = i.find("font", color="#117743")
    if(name):
        name = name.b
        if(name.has_attr("a")):
            resp['name'] = name.string
            # メールアドレスを抽出する細工
            resp['mail'] = name.a.href.split(":")[0]
        else:
            resp['name'] = name.string
            resp['mail'] = ""
    else:
        resp["name"] = ""
        resp["mail"] = ""
    
    # 画像を貼っているひとだったら
    image = i.find("a", target="_blank")
    if(image):
        resp['imgurl'] = image.get("href")
    else:
        resp['imgurl'] = ""
    
    # 日付を抽出
    date_re = re.compile(u'\d{2}/\d{2}/\d{2}\((?:日|月|火|水|木|金|土)\)\d{2}:\d{2}:\d{2} No\.\d*')
    resp['time'] = date_re.findall(i.get_text())[0]

    # そうだねの抽出
    sod = i.find("a", class_="sod")
    if(sod):
        resp["sod"] = sod.string
    else:
        resp["sod"] = ""

    return resp

if(__name__=='__main__'):
    main()
