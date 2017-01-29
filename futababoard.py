#!/usr/bin/python
# -*- coding:utf-8 -*-

from bs4 import BeautifulSoup
import re
import json

def main():
    f = open("cat.html", "r")
    html = f.read().decode("cp932")
    f.close()
    board = get_board(html)
    print(json.dumps(board['thread'], indent=2))

def get_board(html):
    board = {}
    board['thread'] = []
    bs = BeautifulSoup(html, "html.parser")
    board['board_title'] = bs.title.get_text()
    threadnum = re.compile('res/(\d*)\.htm')

    for i in bs.find_all("td"):
        thread = {}

        url = threadnum.match(i.a.get("href"))
        thread['threadid'] = url.group(1)

        if(i.a.img):
            thread['imgurl'] = i.a.img.get("src")
        else:
            thread['imgurl'] = ""
        thread['title'] = i.small.get_text()
        thread['num'] = i.find("font", size="2").get_text()

        board['thread'].append(thread)

    return board

if(__name__=='__main__'):
    main()
