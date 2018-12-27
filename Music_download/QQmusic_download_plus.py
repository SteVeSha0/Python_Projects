# -*- coding: utf-8 -*-
# @Author: kjjdas
# @updater: ss

import requests
import urllib
import json
import os
from lxml import etree
import time

# 准备全局变量
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.63 Safari/537.36 Qiyu/2.1.1.1",
    "Referer": "https://y.qq.com/portal/player.html"
}

def get_song_list(keyword):
    keyword = urllib.parse.quote(keyword)
    url = 'https://c.y.qq.com/soso/fcgi-bin/client_search_cp?aggr=1&cr=1&p=1&n=20&w=%s' % keyword
    response = requests.get(url, headers=headers).text.encode(
        'gbk', 'ignore').decode('gbk').split('callback')[-1].strip('()')
    response = json.loads(response)
    return response['data']['song']

def print_info(songs):
    for num, song in enumerate(songs):
        songname = song['songname']
        singer_length = len(song['singer'])
        singers = []
        for i in range(singer_length):
            singers.append(song['singer'][i]['name'])
        singers = ('/').join(singers)
        # album_mid = song['albummid']
        album_name = song['albumname']
        # song_midcode = song['songmid']
        time = song['interval']
        m, s = divmod(time, 60)
        time = "%02d:%02d" % (m, s)
        print(num,'歌曲名字：', songname, '作者：' ,singers, '专辑：', album_name, '时长：', time)

def get_mp3(songs,num):
    albummid = songs['list'][num]['albummid'] 
    url = "https://c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg?albummid=" + albummid + "&g_tk=5381&jsonpCallback=albuminfoCallback&loginUin=0&hostUin=0&format=jsonp&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0"
    headers['Referer'] = "https://y.qq.com/portal/player.html"
    ie = requests.session()
    rep = ie.get(url, headers=headers)
    html = rep.content.decode('utf-8')[19:-1]
    song_list = json.loads(html)['data']['list']
    for song in song_list:
        song_name = song['songname']
        if song_name == songs['list'][num]['songname']:
            song_mid = song['songmid']
            get_key_url = "https://u.y.qq.com/cgi-bin/musicu.fcg?callback=getplaysongvkey0996617262271613&g_tk=5381&jsonpCallback=getplaysongvkey0996617262271613&loginUin=0&hostUin=0&format=jsonp&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0&data=%7B%22req_0%22%3A%7B%22module%22%3A%22vkey.GetVkeyServer%22%2C%22method%22%3A%22CgiGetVkey%22%2C%22param%22%3A%7B%22guid%22%3A%228216405924%22%2C%22songmid%22%3A%5B%22" + song_mid + "%22%5D%2C%22songtype%22%3A%5B0%5D%2C%22uin%22%3A%220%22%2C%22loginflag%22%3A1%2C%22platform%22%3A%2220%22%7D%7D%2C%22comm%22%3A%7B%22uin%22%3A0%2C%22format%22%3A%22json%22%2C%22ct%22%3A20%2C%22cv%22%3A0%7D%7D"
            rep = ie.get(get_key_url, headers=headers)
            html = rep.content.decode('utf-8')[32:-1]
            data = json.loads(html)['req_0']['data']
            download_url_1 = data['sip'][0]
            download_url_2 = data['midurlinfo'][0]['purl']
            filename = data['midurlinfo'][0]['filename']
            url = download_url_1 + download_url_2
            rep = ie.get(url, headers=headers, stream=True)
            # 此处工作目录下要有qqmusicdownload文件夹
            with open('./qqmusicdownload/%s' % (song_name + "-" + "-" + filename), 'wb') as file:
                for byte_data in rep.iter_content(1024):
                    file.write(byte_data)
            print('《%s》 已成功下载到qqmusicdownload目录下！' % song_name)
            time.sleep(2)

def run():
    while  True:
        name = input('请输入你要下载的歌曲：')
        songs = get_song_list(name)
        if songs['totalnum'] == 0 : 
            print('没有搜到此歌曲，请换个关键字')
        else:
            print_info(songs['list'])
            num = input('请输入需要下载的歌曲，输入左边对应数字即可')
        get_mp3(songs,int(num))
        
        flag = input('如需继续可以按任意键进行搜歌，否则按0结束程序')
        if flag == '0':
            break

def main():
    if os.path.exists('.\\qqmusicdownload') == False:
        os.mkdir('.\\qqmusicdownload')
    run()

if __name__ == '__main__':
    main()
