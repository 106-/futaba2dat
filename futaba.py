#!/usr/bin/python
# -*- coding:utf-8 -*-

from bottle import route, run, template, response
from bs4 import BeautifulSoup
import urllib
import urllib2
import re
import cookielib
import os
import futabathread
import futababoard

FUTABA_CAT_URL = 'http://%s.2chan.net/%s/futaba.php?mode=cat'
FUTABA_CATSET_URL = 'http://%s.2chan.net/%s/futaba.php?mode=catset'
futaba_thread_url = 'http://%s.2chan.net/%s/res/%s.htm'
futaba_url = 'http://%s.2chan.net'
futaba_encoding = 'cp932'
futaba_boards = {('zip','1'): u'野球＠ふたば',
('zip','12'): u'サッカー＠ふたば',
('may','25'): u'麻雀＠ふたば',
('may','26'): u'うま＠ふたば',
('may','27'): u'ねこ＠ふたば',
('dat','d'): u'どうぶつ＠ふたば',
('zip','z'): u'しょくぶつ＠ふたば',
('dat','w'): u'虫＠ふたば',
('dat','49'): u'アクアリウム＠ふたば',
('dat','t'): u'料理＠ふたば',
('dat','20'): u'甘味＠ふたば',
('dat','21'): u'ラーメン＠ふたば',
('dat','e'): u'のりもの＠ふたば',
('dat','j'): u'二輪＠ふたば',
('nov','37'): u'自転車＠ふたば',
('dat','45'): u'カメラ＠ふたば',
('dat','48'): u'家電＠ふたば',
('dat','r'): u'鉄道＠ふたば',
('dat','img2'): u'二次元画像掲示板＠ふたば',
('dec','b'): u'二次元裏＠ふたば',
('jun','b'): u'二次元裏＠ふたば',
('may','b'): u'二次元裏＠ふたば',
('img','b'): u'二次元裏＠ふたば',
('dec','58'): u'二次元裏転載不可＠ふたば',
('dec','59'): u'二次元裏転載可＠ふたば',
('may','id'): u'二次元ID＠ふたば',
('dat','23'): u'スピグラ＠ふたば',
('dat','16'): u'二次元ネタ＠ふたば',
('dat','43'): u'二次元業界＠ふたば',
('jun','31'): u'ゲーム＠ふたば',
('nov','28'): u'ネトゲ＠ふたば',
('dec','56'): u'ソーシャルゲーム＠ふたば',
('dec','60'): u'艦これ＠ふたば',
('dec','61'): u'ソニー＠ふたば',
('dat','10'): u'ネットキャラ＠ふたば',
('nov','34'): u'なりきり＠ふたば',
('zip','11'): u'自作絵＠ふたば',
('zip','14'): u'自作絵裏＠ふたば',
('zip','32'): u'女装＠ふたば',
('zip','15'): u'ばら＠ふたば',
('zip','7'): u'ゆり＠ふたば',
('zip','8'): u'やおい＠ふたば',
('cgi','o'): u'二次元グロ＠ふたば',
('jun','51'): u'二次元グロ裏＠ふたば',
('zip','5'): u'えろげ＠ふたば',
('zip','3'): u'自作PC＠ふたば',
('cgi','g'): u'特撮＠ふたば',
('zip','2'): u'ろぼ＠ふたば',
('dat','44'): u'おもちゃ＠ふたば',
('dat','v'): u'模型＠ふたば',
('nov','y'): u'模型裏＠ふたば',
('dat','46'): u'フィギュア＠ふたば',
('dat','x'): u'三次元ＣＧ＠ふたば',
('nov','35'): u'政治＠ふたば',
('nov','36'): u'経済＠ふたば',
('dec','50'): u'三次実況＠ふたば',
('dat','38'): u'韓国経済＠ふたば',
('cgi','f'): u'軍＠ふたば',
('may','39'): u'軍裏＠ふたば',
('cgi','m'): u'数学＠ふたば',
('cgi','i'): u'FLASH＠ふたば',
('cgi','k'): u'壁紙＠ふたば',
('dat','l'): u'二次元壁紙＠ふたば',
('may','40'): u'東方＠ふたば',
('dec','55'): u'東方裏＠ふたば',
('zip','p'): u'お絵かき＠ふたば',
('nov','q'): u'落書き＠ふたば',
('cgi','u'): u'落書き裏＠ふたば',
('zip','6'): u'ニュース表＠ふたば',
('dec','53'): u'発電＠ふたば',
('dec','52'): u'東日本大震災＠ふたば',
('img','9'): u'雑談＠ふたば',
('www','script'): u'配布＠ふたば',
#('dat','22'): u'人形・ドール＠ふたば',
('jun','oe'): u'お絵sql＠ふたば',
('jun','junbi'): u'準備＠ふたば',
}
FUTABA_CAT_TERM = "<td><a href='(.*)' target='_blank'>(.*)<font size=2>(.*)</font></td>"

############################################################

# トップページ
@route('/', method='get')
def add_get():
    response.content_type = 'text/html; charset="shift_jis"'
    return template('top', keys=futaba_boards.keys(), boards=futaba_boards)
# 各板のページ
@route('/<subadr>_<board>/subject.txt')
def add_get(subadr,board):
    response.content_type = 'text/plain; charset="shift_jis"'
    return makesubject({'subaddr':subadr, 'bdname':board}).encode(futaba_encoding, 'ignore')
# 各板の名前を返すページ
@route('/<subadr>_<board>/SETTING.TXT')
def add_get(subadr,board):
    response.content_type = 'text/plain; charset="shift_jis"'
    return u'BBS_TITLE=%s'%(getboardname({'subaddr':subadr, 'bdname':board})).encode(futaba_encoding, 'ignore')
# トップページを開いたときのタイトルを各板の名前にしておく(2chmateで有効だった)
@route('/<subadr>_<board>/')
def add_get(subadr,board):
    response.content_type = 'text/plain; charset="shift_jis"'
    return (u'<title>%s</title>'%getboardname({'subaddr':subadr, 'bdname':board})).encode(futaba_encoding, 'ignore')
# スレッドのページ
@route('/<subadr>_<board>/dat/<datnum:int>.dat')
def add_get(subadr,board,datnum):
    response.content_type = 'text/plain; charset="shift_jis"'
    return makedat({'subaddr':subadr, 'bdname':board}, datnum).encode(futaba_encoding, 'ignore')

############################################################

#urlをいい感じに変換
def parseurl(url):
    slashurl = url.split('/')
    hosturl = slashurl[2].split('.')
    addr = { 'subaddr':hosturl[0], 'bdname':slashurl[3] }
    return addr

#いい感じをurlに変換
def parseaddr(url,addr,thread=0):
    if(thread == 0):
        return url%(addr['subaddr'], addr['bdname'])
    else:
        return url%(addr['subaddr'], addr['bdname'], thread)

#まえしょり
def getopener(addr):
    data = { 'mode':'catset', 'cx':'100', 'cy':'100', 'cl':100 }
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
    res = opener.open(parseaddr(FUTABA_CATSET_URL, addr), urllib.urlencode(data))
    return opener

#ふたばのカタログをgetしてsubject.txtに変換して返す
def makesubject(addr):
    global futaba_boards
    opener = getopener(addr)
    res = opener.open(parseaddr(FUTABA_CAT_URL,addr))
    htm = res.read().decode(futaba_encoding)

    board = futababoard.get_board(htm)
    title = board['board_title']
    futaba_boards[(addr['subaddr'],addr['bdname'])] = title
    subject = ''
    for i in board['thread']:
        # (スレッド番号).dat<>(スレッドタイトル) ((レス数))
        subject += '%s.dat<>%s (%s)\r\n'%(i['threadid'], i['title'], i['num'])
    return subject

#ふたばのスレをdatに変換
def makedat(addr, thread_num):
    res = ''
    # ファイルとってくる
    try:
        res = urllib2.urlopen(parseaddr(futaba_thread_url, addr, thread_num))
    except urllib2.HTTPError, e:
        if(e.code==404):
            response.status = 404
            return u'ファイルが見つからないようです'
        else:
            response.status = e.code
            return u'よくわからないけどエラーです'
    
    htm = res.read().decode(futaba_encoding,'ignore')

    # 特定画像ロダの文字列をURLに置換する
    htm = re.sub('su[0-9]{7}\.(?:jpg|png|gif)',replace,htm)
    # htmlファイルから情報の抽出
    thread = futabathread.get_thread(htm)

    dat = ''
    for i,n in enumerate(thread['response']):
        
        body = []
        body.append(n['body'])
        # 画像があれば
        if(n["imgurl"]):
            body.append((futaba_url % addr['subaddr'])+n['imgurl'])
        # 一番最初のレスに掲示板へのURLを貼る
        if(i==0):
            body.append(parseaddr(futaba_thread_url, addr, thread_num))
        body = "<br>".join(body)
        
        name = []
        for m in [n['title'], n['name'], n['sod']]:
            if(m):
                name.append(m)
        name = ' '.join(name)

        if(i!=0):
            dat += '%s<>%s<>%s<>%s<>\r\n'%(name,
                                        n['mail'], 
                                        n['time'], 
                                        body)
        else:
            dat += '%s<>%s<>%s<>%s<>%s(%s)\r\n'%(name,
                                        n['mail'], 
                                        n['time'], 
                                        body,
                                        thread['title'],
                                        thread['expire'])            
    return dat

#板の名前知ってたら返す
def getboardname(addr):
    if (addr['subaddr'],addr['bdname']) in futaba_boards:
        return futaba_boards[(addr['subaddr'],addr['bdname'])]+'('+addr['subaddr']+'_'+addr['bdname']+')'.decode('utf-8')
    else:
        return 'UNNAMED'+'('+addr['subaddr']+'_'+addr['bdname']+')'.decode('utf-8')

#su0000000.jpg系の画像ファイルをurlに置換
#http://www.nijibox5.com/futabafiles/tubu/src/su1143113.jpg
def replace(m):
    strg = m.group(0)
    return 'http://www.nijibox5.com/futabafiles/tubu/src/%s'%strg

############################################################

def main():
    run(host="0.0.0.0", port=int(os.environ.get("PORT", 80)))

if __name__ == '__main__':
    main()
