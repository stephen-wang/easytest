#!/usr/bin/python3

import logging
from os import path
import socket
import threading
import time

from .envmgr import EnvMgr
from .exceptions import InvalidArgumentError
from .logger import get_logger
from .message import SyncMsg
from .progressmgr import ProgressMgr
from .resultmgr import ResultMgr
from .ssh import SSSHClient, SSHServer
from .testsetmgr import TestsetMgr


logger = get_logger('TestMgr', level=logging.DEBUG)


class TestMgr(object):
    """The wrapper and single entry point of easytest framework, which will
    start and serialize the whole test procedure
    """

    def __init__(self, tests=None, groups=None, servers=None):
        self.tests = tests
        self.groups = groups
        self.servers = servers

        self.testcases = None
        self.daemon = None
        self.daemon_ip = socket.gethostbyname(socket.gethostname())
        self.progress_mgr = None

    def check_server_connectivity(self):
        """Check if requested server is reachable"""

        logger.info('Check connectivity of test servers')
        invalid_servers = {} 
        for server in self.servers:
            try:
                with SSSHClient(server=server):
                   pass
            except Exception as e:
                invalid_servers[server] = str(e)

        if len(invalid_servers) > 0:
            msg = 'Servers can\'t be connected: {}'.format(invalid_servers)
            raise InvalidArgumentError(msg)

    def start_daemon(self, msg_handler):
        logger.info('Start easytest daemon ...')
        self.daemon = SSHServer(msg_handler=msg_handler)
        t = threading.Thread(target=self.daemon.execute)
        t.setDaemon(True)
        t.start()

        # Make sure daemon thread is up before existing this function
        time.sleep(1)
        return t 

    def stop_daemon(self, daemon_thread):
        self.daemon.stop()
        daemon_thread.join()

    def run(self):
        """ Start to run tests. """

        logger.info('Start to run tests') 
        
        # Make sure all requested server are accessible
        self.check_server_connectivity()

        # Collect tests per uer input
        ProgressMgr.print_prompt('Collecting test scripts...')
        self.testcases = TestsetMgr.get_tests(self.tests, self.groups)
        if not self.testcases:
            ProgressMgr.print_prompt('No tests need to be run')
            return

        ProgressMgr.print_prompt('Tests are running\n')

        relpaths = [c.relpath for c in self.testcases]
        with ProgressMgr(relpaths) as pm:
            result_mgr = ResultMgr(self.testcases, pm)

            # Deploy eastest agent scripts to test servers
            self.remote_agent_dir = EnvMgr.deploy_agents(self.servers)

            # Deploy test scripts to test servers
            testscripts = [testcase.abspath for testcase in self.testcases]
            remote_test_dir = EnvMgr.deploy_tests(testscripts, self.servers)

            # Start daemon for syncing up status from test servers
            daemon_thread = self.start_daemon(result_mgr.sync_result)

            # Start to run tests on all test servers
            logger.info('Begin to run tests ...')
            for server in self.servers:
                agent_script = path.join(self.remote_agent_dir, 'remoterun.py')
                cmdFmt = '{} --testdir {} --sync --server {}'
                cmd = cmdFmt.format(agent_script, remote_test_dir, self.daemon_ip)
                logger.debug('Start to run tests on {}, cmd:{}'.format(server, cmd))
                with SSSHClient(server=server) as sshClient:
                    sshClient.exec_command('cd {}'.format(self.remote_agent_dir))
                    sshClient.exec_command('nohup {} &'.format(cmd))

            # Wait for all tests finish
            while not result_mgr.tests_done:
                time.sleep(2)

            # Stop easytest daemon and exit
            self.stop_daemon(daemon_thread)

        logger.info('All tests are finished: %s', result_mgr.info())
