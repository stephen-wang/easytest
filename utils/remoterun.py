#!/usr/bin/python3

"""The eastest agent on test server, which is responsible for running tests one
by one, syncing up test progress with easytest, collecting, and sending back
test result.
""" 

import argparse
import glob
from os import path
import random
import subprocess
import time

from utils.exceptions import SessionBrokenError
from utils.ssh import SSHClient
from utils.message import SyncMsg, AckMsg
from utils.resultmgr import TestResult


class EasytestAgent(object):
    def __init__(self, server):
        self.server = server
        self.msg_id = 0
        self.client = None

    def connect(self):
        random.seed(time.time())
        self.msg_id = random.randint(5000, 50000)
        self.client = SSHClient(self.server)
        self.client.connect()
        return self

    def disconnect(self, exec_type, exec_val, exec_tb):
        if self.client:
            self.client.close()

    def update_test_progress(self, tests, status):
        msg = SyncMsg(testscript, status)
        resp = AckMsg(msg.msgid)
        self.notify(msg.val, resp.val)

    def notify_test_done(self):
        msg = SyncMsg('all', TestResult.FINISHED)
        resp = AckMsg(msg.msgid)
        self.notify(msg.val, resp.val)

    def notify(self, req, expect_resp):
        retries = 0
        MAX_RETRIES = 3

        self.client.send(req)
        ack = self.client.recv()
        while retries < MAX_RETRIES and ack != expect_resp:
            self.client.send(req)
            self.client.recv(ack)
            retries += 1

        if retries == MAX_RETRIES:
            error = 'Can\'t sync up with server ({})'.format(req)
            raise SessionBroeknError(error)


def get_args():
    """Construct and return supported arguments"""

    desc = 'run.py is the entry of easy test frameworkt'
    argparser = argparse.ArgumentParser(description=desc)

    argparser.add_argument('--testdir', help='The server directory where test '\
                           'scripts are located', action='store', required=True)
    argparser.add_argument('--sync', help='indicate if to sync with easy with '\
                           'easytest', action='store_true')
    argparser.add_argument('--server', help='the easytest server with which to '\
                           'sync the test progress', action='store')
    args = argparser.parse_args()
    if not args.sync and args.server or args.sync and not args.server:
        raise SystemExit('option "--server" and "--sync" must be used together')
    return args


if __name__ == '__main__':
    args = get_args()

    agent = None
    if args.sync: 
        agent= EasytestAgent(args.server)
        agent.connect()

    search_path = path.join(args.testdir, '**/*.*')
    for testscript in glob.glob(search_path, recursive=True):
        status = TestResult.RUNNING
        agent.update_test_progress(testscript, status)
        try:
            subprocess.check_output([testscript])
            status = TestResult.FINISHED
        except Exception as e:
            status = TestResult.FAILED
        if args.sync:
            agent.update_test_progress(testscript, status)
    agent.notify_tests_done()
