#!/usr/bin/python3

from .envmgr import EnvMgr
from .exceptions import InvalidArgumentError
from .message import SyncMsg
#from .sessionMgr import SessionMgr
from .ssh import SSSHClient, SSHServer
#from .resultMgr import ResultMgr
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
        self.session_mgr = None
        self.daemon = SSHServer(msg_handler=SyncMsg.ack_msg)

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

    def run(self):
        """ Start to run tests. """
        
        import socket

        # Make sure all requested server are accessible
        self.check_server_connectivity()

        # Collect tests per uer input
        self.testcases = TestsetMgr.get_tests(self.tests, self.groups)

        # Deploy eastest agent scripts to test servers
        self.remote_agent_dir = EnvMgr.deploy_agents(self.servers)

        # Deploy test scripts to test servers
        testscripts = [testcase.script for testcase in self.testcases]
        remote_test_dir = EnvMgr.deploy_tests(testscripts, self.servers)

        '''
        # Start daemon for syncing up status from test servers
        t = threading.Thread(target=self.daemon.start())
        t.start()

        # Start to run tests on all test servers
        for server in self.servers:
            agent_script = path.join(self.remote_agent_dir, 'remoterun.py')
            cmd = '{} --testdir {} -sync --daemon {}'.format(agent_script,
                                                             remote_test_dir,
                                                             socket.gethostname())
            with SSSHClient(server=server) as sshClient:
                sshClient.exec_command('nohup {} &'.format(cmd)

        t.join()
        '''
