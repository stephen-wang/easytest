#!/usr/bin/python3

from os import path
import threading
import time

from .envmgr import EnvMgr
from .exceptions import InvalidArgumentError
from .message import SyncMsg
from .resultmgr import ResultMgr
from .ssh import SSSHClient, SSHServer
from .testsetmgr import TestsetMgr


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

    def check_server_connectivity(self):
        """Check if requested server is reachable"""

        print('Check connectivity of test servers')
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
        print('Start easytest daemon ...')
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
        
        import socket

        # Make sure all requested server are accessible
        self.check_server_connectivity()

        # Collect tests per uer input
        self.testcases = TestsetMgr.get_tests(self.tests, self.groups)
        result_mgr = ResultMgr(self.testcases)

        # Deploy eastest agent scripts to test servers
        self.remote_agent_dir = EnvMgr.deploy_agents(self.servers)

        # Deploy test scripts to test servers
        testscripts = [testcase.script for testcase in self.testcases]
        remote_test_dir = EnvMgr.deploy_tests(testscripts, self.servers)

        # Start daemon for syncing up status from test servers
        self.daemon = SSHServer(msg_handler=result_mgr.sync_result)
        daemon_thread = self.start_daemon(result_mgr.sync_result)

        # Start to run tests on all test servers
        print('Begin to run tests ...')
        for server in self.servers:
            agent_script = path.join(self.remote_agent_dir, 'remoterun.py')
            cmd = '{} --testdir {} --sync --server {}'.format(agent_script,
                                                             remote_test_dir,
                                                             socket.gethostname())
            print('Start to run tests on {}, cmd:{}'.format(server, cmd))
            with SSSHClient(server=server) as sshClient:
                sshClient.exec_command('cd {}'.format(self.remote_agent_dir))
                sshClient.exec_command('nohup {} &'.format(cmd))

        # Wait for all tests finish
        while result_mgr.not_run() > 0:
            time.sleep(2)

        print('All tests are finished:', result_mgr.info())

        # Stop easytest daemon and exit
        self.stop_daemon(daemon_thread)
