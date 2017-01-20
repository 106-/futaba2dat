# -*- coding:utf-8 -*-

import sys, os

dirpath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(dirpath)
os.chdir(dirpath)

import bottle
import futaba

application = bottle.default_app()
