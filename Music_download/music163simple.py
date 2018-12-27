#!python3
# -*- coding:utf-8 -*-
# 获取网易云音乐单曲下载

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


