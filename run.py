#!/usr/bin/python3 -u

from os import path
import sys

from utils.args import get_args
from utils.testmgr import TestMgr 

sys.path.append(path.dirname(__file__))


if __name__ == '__main__':
    args = get_args()
    TestMgr(args.test, args.group, args.server).run()
