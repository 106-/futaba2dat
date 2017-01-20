#!/usr/bin/python
# -*- coding:utf-8 -*-

from bottle import route, run, template, response
import urllib
import urllib2
import re
import cookielib
import os

FUTABA_CAT_URL = 'http://%s.2chan.net/%s/futaba.php?mode=cat'
FUTABA_CATSET_URL = 'http://%s.2chan.net/%s/futaba.php?mode=catset'
FUTABA_THREAD_URL = 'http://%s.2chan.net/%s/res/%s.htm'
FUTABA_ENCODING = 'cp932'
FUTABA_MOJISU = 100
FUTABA_BOARDLST = {('zip','1'): u'野球＠ふたば',
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
FUTABA_THREADMASTER_TERM = u"(?:画像ファイル名\：<a href=\"(?P<imgurl>.*)\" target=\"_blank\">(?:.*)</a>(?:.*)<small>サムネ表示</small><br><a href.*?><img src.*?></a>)?<input type.*?>(?:<font color='#cc1105'><b>(?P<title>.*)</b></font> \nName <font color='#117743'><b>(?:<a href=\"mailto\:(?P<mail>.*)\">)?(?P<name>.*) (?:</a>)?</b></font>)? ?(?P<time>.*?) ?(?:<a class=del href=\".*?\">del</a>)?\n<small>(?P<expire>.*)</small>\n<blockquote>(?P<body>.*)</blockquote>"
FUTABA_RESPONSE_TERM = u"<input type=checkbox name=\".*\" value=delete id=delcheck.*>(?:<font color='#cc1105'><b>(?P<title>.*)</b></font> \nName <font color='#.*'><b>(?:<a href=\"mailto\:(?P<mail>.*)\">)?(?P<name>.*) (?:</a>)?</b></font>)? ?(?P<time>.*) ?<a class=del href=\"javascript:void\(0\);\" onclick=\"del\(.*\);return\(false\);\">del</a>\n(?:<br> &nbsp; &nbsp; <a href=\".*\" target=\"_blank\">.*</a>-\(.* B\) <small>サムネ表示</small><br><a href=\"(?P<imgurl>.*)\" target=\"_blank\"><img src.*?></a>)?<blockquote(?:.*?)>(?P<body>.*)</blockquote>"

############################################################

@route('/', method='get')
def add_get():
    response.content_type = 'text/html; charset="shift_jis"'
    return template('top', keys=FUTABA_BOARDLST.keys(), boards=FUTABA_BOARDLST)

@route('/<subadr>_<board>/subject.txt')
def add_get(subadr,board):
    response.content_type = 'text/plain; charset="shift_jis"'
    return makesubject({'subaddr':subadr, 'bdname':board}).encode(FUTABA_ENCODING)

@route('/<subadr>_<board>/SETTING.TXT')
def add_get(subadr,board):
    response.content_type = 'text/plain; charset="shift_jis"'
    return u'BBS_TITLE=%s'%(getboardname({'subaddr':subadr, 'bdname':board})).encode(FUTABA_ENCODING)

@route('/<subadr>_<board>/')
def add_get(subadr,board):
    response.content_type = 'text/plain; charset="shift_jis"'
    return (u'<title>%s</title>'%getboardname({'subaddr':subadr, 'bdname':board})).encode(FUTABA_ENCODING)

@route('/<subadr>_<board>/dat/<datnum:int>.dat')
def add_get(subadr,board,datnum):
    response.content_type = 'text/plain; charset="shift_jis"'
    return makedat({'subaddr':subadr, 'bdname':board}, datnum).encode(FUTABA_ENCODING)

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
    data = { 'mode':'catset', 'cx':'10', 'cy':'10', 'cl':FUTABA_MOJISU }
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
    res = opener.open(parseaddr(FUTABA_CATSET_URL, addr), urllib.urlencode(data))
    return opener

#ふたばのカタログをgetしてsubject.txtに変換して返す
def makesubject(addr):
    global FUTABA_BOARDLST
    opener = getopener(addr)
    res = opener.open(parseaddr(FUTABA_CAT_URL,addr))
    htm = res.read().decode(FUTABA_ENCODING)
    threadlst = re.findall(FUTABA_CAT_TERM, htm)
    title = re.findall('<title>(.*)</title>', htm)[0]
    FUTABA_BOARDLST[(addr['subaddr'],addr['bdname'])] = title
    subject = ''
    for i in threadlst:
        title = i[1].replace('<small>','').replace('</small>','').replace('</a>','').replace('<br>','')
        title = re.sub("<img src='.*' border=0 width=.* height=.* alt=\"\">", '', title)
        #print(i[0])
        subject += '%s.dat<>%s (%s)\r\n'%(i[0][4:-4], title, i[2])
    return subject

#名前<>メール欄<>日付、ID<>本文<>スレタイトル(1行目のみ存在する)\n
#ふたばのスレをdatに変換
def makedat(addr, thread):
	res = ''
	try:
		res = urllib2.urlopen(parseaddr(FUTABA_THREAD_URL, addr, thread))
	except urllib2.HTTPError, e:
		if(e.code==404):
			response.status = 404
			return u'ファイルが見つからないようです'
		else:
			response.status = e.code
			return u'よくわからないけどエラーです'
		
	htm = res.read().decode(FUTABA_ENCODING,'ignore')
	htm = re.sub('su[0-9]{7}\.(?:jpg|png|gif)',replace,htm)
	dat = ''

	master = re.findall(FUTABA_THREADMASTER_TERM, htm)[0]
	body = (master[0]+'<br>'+master[6] if len(master[0]) != 0 else master[6]) +'<br><br>'+ parseaddr(FUTABA_THREAD_URL, addr, thread)
	dat += '%s<>%s<>%s<>%s<>%s(%s)\r\n'%(master[1]+'_'+master[3], master[2], master[4], body, master[6], master[5])
	
	resp = re.findall(FUTABA_RESPONSE_TERM, htm)
	for i in resp:
		body = i[4]+'<br>'+i[5] if len(i[4]) != 0 else i[5]
		dat += '%s<>%s<>%s<>%s<>\r\n'%(i[0]+'_'+i[2], i[1], i[3], body)
	return dat

#板の名前知ってたら返す
def getboardname(addr):
    if (addr['subaddr'],addr['bdname']) in FUTABA_BOARDLST:
        return FUTABA_BOARDLST[(addr['subaddr'],addr['bdname'])]+'('+addr['subaddr']+'_'+addr['bdname']+')'.decode('utf-8')
    else:
        return 'UNNAMED'+'('+addr['subaddr']+'_'+addr['bdname']+')'.decode('utf-8')

#su0000000.jpg系の画像ファイルをurlに置換
#http://www.nijibox5.com/futabafiles/tubu/src/su1143113.jpg
def replace(m):
	strg = m.group(0)
	return 'http://www.nijibox5.com/futabafiles/tubu/src/%s'%strg

############################################################

def main():
	#print(makesubject({'subaddr':'dec', 'bdname':'b'}))
	#print(makedat({'subaddr':'dec', 'bdname':'b'}, 11630396))
	test = re.sub('su[0-9]{7}\.(?:jpg|png|gif)', replace, 'su1143113.jpg')
	print(test)

if __name__ == '__main__':
	#main()
	run(host="0.0.0.0", port=int(os.environ.get("PORT", 80)))
