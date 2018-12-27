#!python3
# -*- coding:utf-8 -*-

import requests
import hashlib
import sys
import click
import re
import base64
import binascii
import json
import eyed3
import os, io
from Crypto.Cipher import AES
from http import cookiejar

"""
Author: Moyuqiezi
"""

class Encrypyed():
    """
    解密算法
    """

    def __init__(self):
        self.modulus = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'
        self.nonce = '0CoJUm6Qyw8W8jud'
        self.pub_key = '010001'

    # 登录加密算法, 基于https://github.com/stkevintan/nw_musicbox脚本实现

    def encrypted_request(self, text):
        text = json.dumps(text)
        sec_key = self.create_secret_key(16)
        enc_text = self.aes_encrypt(self.aes_encrypt(
            text, self.nonce), sec_key.decode('utf-8'))
        enc_sec_key = self.rsa_encrpt(sec_key, self.pub_key, self.modulus)
        data = {'params': enc_text, 'encSecKey': enc_sec_key}
        return data

    def aes_encrypt(self, text, secKey):
        pad = 16 - len(text) % 16
        text = text + chr(pad) * pad
        encryptor = AES.new(secKey.encode('utf-8'),
                            AES.MODE_CBC, b'0102030405060708')
        ciphertext = encryptor.encrypt(text.encode('utf-8'))
        ciphertext = base64.b64encode(ciphertext).decode('utf-8')
        return ciphertext

    def rsa_encrpt(self, text, pubKey, modulus):
        text = text[::-1]
        rs = pow(int(binascii.hexlify(text), 16),
                 int(pubKey, 16), int(modulus, 16))
        return format(rs, 'x').zfill(256)

    def create_secret_key(self, size):
        return binascii.hexlify(os.urandom(size))[:16]


class Spider():
    """网易云爬取API"""

    def __init__(self, timeout=60, cookie_path='.'):
        # self.headers = {
        #     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) \
        #     AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
        # }
        self.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'music.163.com',
            'Referer': 'http://music.163.com/search/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) \
            AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 \
            Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.cookies = cookiejar.LWPCookieJar(cookie_path)
        self.download_session = requests.Session()
        self.timeout = timeout
        self.ep = Encrypyed()

    def post_request(self, url, params):
        """Post请求
        :return:字典
        """

        data = self.ep.encrypted_request(params)
        resp = self.session.post(url, data=data, timeout=self.timeout)
        result = resp.json()
        if result['code'] != 200:
            click.echo('post_request error')
        else:
            return result

    def get_song_url(self, song_id, bit_rate=320000):
        """获得歌曲的下载地址
        :params song_id: 音乐ID<int>
        :params bit_rate: {'MD 128k': 128000, 'HD 320k': 320000}
        :return: 歌曲下载地址
        """

        url = 'http://music.163.com/weapi/song/enhance/player/url?csrf_token='
        csrf = ''
        params = {'ids': [song_id], 'br': bit_rate, 'csrf_token': csrf}
        result = self.post_request(url, params)
        # 歌曲下载地址
        song_url = result['data'][0]['url']

        # 歌曲不存在
        if song_url is None:
            click.echo(
                'Song {} is not available due to copyright issue.'.format(song_id))
        else:
            return song_url
    
    def add_mp3_tag_to_file(self, song_name, song_info, folder):
        """添加mp3文件tag
        :params song_info: 歌曲信息
        :params folder: 歌曲保存目录
        """

        if not os.path.exists(folder):
            os.makedirs(folder)
        fpath = os.path.join(folder, song_name + '.mp3')
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            valid_name = re.sub(r'[<>:"/\\|?*]', '', song_name)
            if valid_name != song_name:
                click.echo('{} will be saved as: {}.mp3'.format(
                    song_name, valid_name))
                fpath = os.path.join(folder, valid_name + '.mp3')

        if os.path.exists(fpath):
            audio = eyed3.load(fpath)
            audio.tag.title = song_name
            audio.tag.artist = song_info['artists_name']
            audio.tag.album = song_info['song_album']
            print('save successed')
            audio.tag.save()

    def download_song(self, song_url, song_name, folder):
        """下载歌曲到本地"""

        if not os.path.exists(folder):
            os.makedirs(folder)
        fpath = os.path.join(folder, song_name + '.mp3')
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            valid_name = re.sub(r'[<>:"/\\|?*]', '', song_name)
            if valid_name != song_name:
                click.echo('{} will be saved as: {}.mp3'.format(
                    song_name, valid_name))
                fpath = os.path.join(folder, valid_name + '.mp3')

        if not os.path.exists(fpath):
            resp = self.download_session.get(
                song_url, timeout=self.timeout, stream=True)
            length = int(resp.headers.get('content-length'))
            label = 'Downloading {} {}kb'.format(song_name, int(length/1024))

            with click.progressbar(length=length, label=label) as progressbar:
                with open(fpath, 'wb') as song_file:
                    for chunk in resp.iter_content(chunk_size=1024):
                        if chunk:
                            song_file.write(chunk)
                            progressbar.update(1024)

    def getLyric(self, song_id, song_name, folder):
        """获取歌词
        :params song_id:歌曲ID
        :params song_name:歌曲名"""
        url = 'http://music.163.com/api/song/lyric?os=pc&id=%s&lv=-1&kv=-1' % song_id
        
        if not os.path.exists(folder):
            os.makedirs(folder)
        fpath = os.path.join(folder, song_name + '.lrc')
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            valid_name = re.sub(r'[<>:"/\\|?*]', '', song_name)
            if valid_name != song_name:
                click.echo('{} will be saved as: {}.lrc'.format(
                    song_name, valid_name))
                fpath = os.path.join(folder, valid_name + '.lrc')

        if not os.path.exists(fpath):
            resp = requests.get(url)
            try:
                lrc = resp.json()['lrc']['lyric']
            except:
                lrc = '纯音乐，无歌词'
            with open(fpath, 'w', encoding='utf-8-sig') as lrc_file:
                lrc_file.write(lrc)

    def getPlaylist(self, playlist_id):
        """获取歌单信息
        :params playlist_id:歌单ID
        :return: 歌单所有歌曲的信息<dict>
        """
        url = 'http://music.163.com/api/playlist/detail?id=%s' % playlist_id
        re = requests.get(url, headers=self.headers)

        # 包括歌曲ID 歌曲名 歌手 专辑
        detail = re.json()['result']['tracks']
        music_list = []
        for x in range(len(detail)):
            info = detail[x]
            artists_name = info["artists"][0]['name']
            for i in range(1, len(info["artists"])):
                artists_name += '&' + info["artists"][i]['name']
            music_list.append(
                {
                    'song_name': info['name'],
                    'artists_name': artists_name,
                    'song_album': info['album']['name'],
                    'song_id': info['id'],
                }
            )

        return music_list


class Netease():
    """网易云音乐下载"""

    def __init__(self, folder, quiet=True, cookie_path='Cookie'):
        self.spider = Spider()
        self.folder = '.' if folder is None else folder
        self.quiet = quiet

    def add_mp3_tag(self, song_name, song_info):
        self.spider.add_mp3_tag_to_file(song_name, song_info, self.folder)

    def download_lrc_by_id(self, song_id, song_name):
        """通过歌曲ID下载歌词
        :params song_id:歌曲ID
        :params song_name:歌曲名
        """

        self.spider.getLyric(song_id, song_name, self.folder)
    
    def download_song_by_id(self, song_id, song_name):
        """通过歌曲ID下载歌曲
        :params song_id: 歌曲ID
        :params song_name: 歌曲名<歌手 - 歌曲名>
        """

        try:
            url = self.spider.get_song_url(song_id)
            # # 去掉非法字符
            # song_name = song_name.replace('/', '')
            # song_name = song_name.replace('.', '')
            self.spider.download_song(url, song_name, self.folder)
        
        except:
            click.echo('download_song_by_id error')


if __name__ == "__main__":
    if not os.path.exists('.\\mymusic'):
        os.mkdir('.\\mymusic')
    output = '.\\mymusic'

    netease = Netease(output)


    print('请粘贴歌单地址：')
    user_url = input()
    url = user_url
    playlist_id = re.match(r'(.*?)id=(\d*)', url).groups()[-1]

    playlist_song_info = netease.spider.getPlaylist(playlist_id)
    
    for song_info in playlist_song_info:
        # 水木年华 - 一生有你
        song_name = song_info['artists_name'] + ' - ' + song_info['song_name']
        # 去掉非法字符
        song_name = song_name.replace('/', '&')
        song_name = song_name.replace('.', '')
        song_id = song_info['song_id']
        netease.download_lrc_by_id(song_id, song_name)
        netease.download_song_by_id(song_id, song_name)
        # netease.add_mp3_tag(song_name, song_info)