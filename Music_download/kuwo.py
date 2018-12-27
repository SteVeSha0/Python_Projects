#!/usr/local/bin/python3
# -*- coding:utf-8 -*-

import requests
import re
import os
import sys
import click
from bs4 import BeautifulSoup

"""
Author:Moyuqiezi
"""


class Crawler():
    """酷我音乐爬取API
    """

    # 下载aac文件,基于https://blog.csdn.net/weixin_41796207/article/details/80756995
    def __init__(self):
        self.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'identity;q=1, *;q=0',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Host': 'antiserver.kuwo.cn',
            'Range': 'bytes=0-',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
            'Referer': 'http://www.kuwo.cn/'
        }
        self.session = requests.session()
        self.download_session = requests.Session()

    def request_bs(self, url):
        """请求网页 & 解析
        :return BeautifuSoup object
        """
        
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "lxml")
        return soup

    def get_base_number(self, base_url):
        """获取歌曲ID和歌曲名
        :params base_url:音乐播放页面url
        return: 歌曲ID
        """

        base_url = base_url.strip()
        base_number = re.findall(
            r"(?:http://www.kuwo.cn/yinyue/)(\d+)(?:\?*)", base_url)[0]

        return base_number

    def get_song_name(self, base_url):
        """获取歌曲名
        """

        soup = self.request_bs(base_url)
        song_name = str(soup.find('p', id="lrcName"))[16:-4]
        return song_name

    def get_song_url(self, base_number):
        """获取歌曲下载地址
        :params base_number: 音乐ID<str>
        :return: 歌曲下载地址
        """

        url = "http://antiserver.kuwo.cn/anti.s?format=aac|mp3&rid=MUSIC_" + \
            base_number + "&type=convert_url&response=res"
        r = self.session.get(url, headers=self.headers, allow_redirects=False)
        return r.headers['Location']

    def get_aac(self, song_url):
        """获取到aac文件数据
        :params song_url:歌曲下载地址
        """

        # 修改请求头
        base_host = re.findall(r"(?:http://)(.*)", song_url)[0]
        base_host = base_host.split('/')[0]
        self.headers['Host'] = base_host
        self.headers['Referer'] = song_url

        r = self.download_session.get(
            song_url, headers=self.headers, stream=True)
        return r

    def save_aac(self, song_url, song_name, folder):
        """保存歌曲到本地
        :params songurl: 歌曲下载地址
        :params song_name: 歌曲名字
        :params folder: 保存路径
        """
        if not os.path.exists(folder):
            os.makedirs(folder)
        fpath = os.path.join(folder, song_name + '.aac')
        print(fpath)
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            valid_name = re.sub(r'[<>:"/\\|?*]', '', song_name)
            if valid_name != song_name:
                click.echo('{} will be saved as: {}.aac'.format(
                    song_name, valid_name))
                # fpath = os.path.join(folder, str(song_num) + '_' + valid_name + '.mp3')
                fpath = os.path.join(folder, valid_name + '.aac')

        if not os.path.exists(fpath):
            resp = self.download_session.get(song_url)
            length = int(resp.headers.get('content-length'))
            label = 'Downloading {} {}kb'.format(song_name, int(length/1024))

            with click.progressbar(length=length, label=label) as progressbar:
                with open(fpath, 'wb') as song_file:
                    for chunk in resp.iter_content(chunk_size=1024):
                        if chunk:
                            song_file.write(chunk)
                            progressbar.update(1024)
                print("Downloading {}.aac Done.".format(song_name))


class Kuwo():
    """酷我音乐下载
    """

    def __init__(self, folder):
        self.crawler = Crawler()
        self.folder = '.' if folder is None else folder

    def download_song(self, base_url):
        """下载歌曲
        :params base_url: 音乐播放页面url
        # http://www.kuwo.cn/yinyue/512837/
        """

        song_name = self.crawler.get_song_name(base_url)
        base_number = self.crawler.get_base_number(base_url)
        song_url = self.crawler.get_song_url(base_number)
        self.crawler.save_aac(song_url, song_name, self.folder)

    def download_listMusic(self, url):
        """下载歌手的歌曲列表
        :params url: 歌手页面url
        # http://www.kuwo.cn/artist/content?name=周杰伦
        """
        
        cma = 'http://www.kuwo.cn/artist/contentMusicsAjax?artistId='

        # 获取artistid
        soup = self.crawler.request_bs(url)
        artistid = re.findall(
            r'(?:<div class="artistTop" data-artistid=")(\d+)(?:.)',
            str(soup.find_all('div', 'artistTop')))[0]

        # 获取歌手所有的歌
        content_url = cma + artistid + '&pn=0&rn=15'
        soup = self.crawler.request_bs(content_url)
        page = int(re.findall(
            r'(?:data-page=")(\d+)',
            str(soup.find_all('ul', "listMusic"))
        )[0])
        rn = re.findall(
            r'(?:data-rn=")(\d+)',
            str(soup.find_all('ul', "listMusic"))
        )[0]
        # 计算amount of song
        amountofSong = int(page) * int(rn)
        # http://www.kuwo.cn/artist/contentMusicsAjax?artistId=117925&pn=0&rn=15
        # 修改 rn 为所有歌的数  获取歌手所有歌曲id
        url = cma + artistid + '&pn=0&rn=' + str(amountofSong)
        soup = self.crawler.request_bs(url)
        music_item = str(soup.find_all('div', "name")).split(',')
        num = len(music_item)
        num = 10    # 下载前10首
        for index in range(num):
            # print(music_item[index])
            song_number = re.findall(
                r'(?:/yinyue/)(\d+)',
                music_item[index]
            )[0]
            url = 'http://www.kuwo.cn/yinyue/' + song_number
            self.download_song(url)
            

if __name__ == "__main__":
    folder = 'G:\\music'
    kuwo = Kuwo(folder)

    base_url = 'http://www.kuwo.cn/album/5448220?catalog=yueku2016'  # 忘记时间
    kuwo.download_song(base_url)