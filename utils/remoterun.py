#!/usr/bin/python3

"""The eastest agent on test server, which is responsible for running tests one
by one, syncing up test progress with easytest, collecting, and sending back
test result.
""" 

import argparse
import glob
import logging
from os import path
import subprocess
import time

from utils.configmgr import ConfigMgr
from utils.logger import get_logger
from utils.exceptions import SessionBrokenError
from utils.ssh import SSHConnector
from utils.message import SyncMsg, AckMsg
from utils.resultmgr import TestResult


logger = get_logger('easytestagent', level=logging.DEBUG, is_agent=True)


class EasytestAgent(object):
    _CONFIG_FILE = path.join(path.dirname(path.abspath(__file__)), 'config.ini')
    def __init__(self, server):
        self.server = server
        self.connector= None

    def connect(self):
        logger.info('Connect to server %s', self.server)
        config_mgr = ConfigMgr(config_file=EasytestAgent._CONFIG_FILE)
        self.connector= SSHConnector(self.server, port=config_mgr.daemon_port,
                                     username=config_mgr.daemon_username,
                                     password=config_mgr.daemon_password)
        self.connector.connect()
        return self

    def disconnect(self, exec_type, exec_val, exec_tb):
        if self.connector:
            self.connecctor.close()
        logger.info('Disconnected from server %s', self.server)

    def update_test_progress(self, testscript, status):
        logger.info('Sync-up status to server: %s --- %s', testscript, status.value)
        msg = SyncMsg(testscript, status.value)
        resp = AckMsg(msg.msgid)
        self.notify(msg.val, resp.val)

    def notify_tests_done(self):
        logger.info('Notify server all tests are finished')
        msg = SyncMsg('all', TestResult.FINISHED.value)
        resp = AckMsg(msg.msgid)
        self.notify(msg.val, resp.val)

    def notify(self, req, expect_resp):
        retries = 0
        MAX_RETRIES = 3

        self.connector.send(req)
        ack = self.connector.recv()
        while retries < MAX_RETRIES and ack != expect_resp:
            logger.debug('Sync-up [%s] failed, retry(%d)', req, retries)
            self.connector.send(req)
            self.connector.recv(ack)
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
        logger.info('Start to run %s', testscript)
        status = TestResult.RUNNING
        test_rel_path = path.relpath(testscript, args.testdir)
        agent.update_test_progress(test_rel_path, status)
        try:
            subprocess.check_output([testscript])
            status = TestResult.FINISHED
        except Exception as e:
            logg.info('Test failed: %s', str(e))
            status = TestResult.FAILED
        if args.sync:
            agent.update_test_progress(test_rel_path, status)
    agent.notify_tests_done()
