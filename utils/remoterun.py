#!/usr/bin/python3

"""The eastest agent on test server, which is responsible for running tests one
by one, syncing up test progress with easytest, collecting, and sending back
test result.
""" 

import argparse
import glob
import logging
import os
from os import path
import socket
import subprocess
import time

from utils.configmgr import ConfigMgr
from utils.logger import get_logger
from utils.exceptions import SessionBrokenError
from utils.ssh import SSHConnector
from utils.message import SyncMsg, AckMsg
from utils.resultmgr import make_tarfile, TestResult


logger = get_logger('easytestagent', level=logging.DEBUG, is_agent=True)


class EasytestAgent(object):

    _CONFIG_FILE = path.join(path.dirname(path.abspath(__file__)), 'config.ini')

    def __init__(self, server):
        self.server = server
        self.connector= None

    def connect(self):
        logger.info('Connect to server %s', self.server)
        config_mgr = ConfigMgr(config_file=EasytestAgent._CONFIG_FILE)
        self.connector = SSHConnector(self.server, port=config_mgr.daemon_port,
                                      username=config_mgr.daemon_username,
                                      password=config_mgr.daemon_password)
        self.connector.connect()
        return self

    def open_session(self):
        t = paramiko.Transport((self.server, self.port))
        t.connect(username=self.username, password=self.password)
        return paramiko.SFTPClient.from_transport(t)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb): 
        if self.connector:
            self.connector.close()
        logger.info('Disconnected from server %s', self.server)

    def update_test_progress(self, testscript, status, support_bundle=None):
        msg = SyncMsg(testscript, status.value, support_bundle=support_bundle)
        logger.info('Sync-up status: %s', str(msg))
        exp_resp = AckMsg(msg.msgid)
        self.notify(msg.val, exp_resp.val)

    def notify_tests_done(self):
        logger.info('Notify server all tests are finished')
        msg = SyncMsg('all', TestResult.FINISHED.value)
        resp = AckMsg(msg.msgid)
        self.notify(msg.val, resp.val)

    def notify(self, req, exp_ack):
        retries = 0
        MAX_RETRIES = 3

        self.connector.send(req)
        ack = self.connector.recv()
        while retries < MAX_RETRIES and ack != exp_ack:
            retries += 1
            logger.debug('Sync-up failed, expect: %s, actual: %s', exp_ack, ack)
            self.connector.send(req)
            self.connector.recv(ack)

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


def run_tests(agent, testdir, sync_daemon):
    """Run all tests under directory 'testdir' """

    test_script_dir = path.join(testdir, 'scripts')
    search_path = path.join(test_script_dir, '**/*.*')
    for testscript in glob.glob(search_path, recursive=True):
        exec_dir = path.join(testdir, 'out', path.basename(testscript))
        if not path.isdir(exec_dir):
            os.makedirs(exec_dir)

        status = TestResult.RUNNING
        test_rel_path = path.relpath(testscript, test_script_dir)
        agent.update_test_progress(test_rel_path, status)
        try:
            logger.info('Run %s in directory %s', testscript, exec_dir)
            subprocess.check_output([testscript], cwd=exec_dir)
            status = TestResult.FINISHED
        except subprocess.CalledProcessError as e:
            logger.info('Test failed: %s', str(e))
            status = TestResult.FAILED
        except Exception as e:
            logger.info('Test failed: %s', str(e))
            status = TestResult.FAILED

        support_bundle = None
        if status == TestResult.FAILED:
            support_bundle = exec_dir + '.tar.gz'
            make_tarfile(support_bundle, exec_dir)
            ip_addr = socket.gethostbyname(socket.gethostname())
            support_bundle = ip_addr + ':' + support_bundle

        if sync_daemon:
            agent.update_test_progress(test_rel_path, status, support_bundle)

    if sync_daemon:
        agent.notify_tests_done()


if __name__ == '__main__':
    args = get_args()
    with EasytestAgent(args.server) as agent:
        run_tests(agent, args.testdir, args.sync)
