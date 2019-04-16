#!/usr/bin/python3

import glob
from os import path
import random
import stat
import string

from .ssh import SftpClient


class EnvMgr(object):
    """Util class for deploying tests to test machines. """

    _SERVER_DIR_ = "/local"

    @staticmethod
    def get_unique_name(prefix='test_'):
        chars = ''.join([random.choice(string.ascii_lowercase) \
                         for _ in range(8)])
        nums = ''.join([str(random.randint(0,9)) for _ in range(4)])
        return ''.join([prefix, chars, nums])

    @staticmethod
    def deploy_agents(servers, username='stephenw', password='ca$hc0w'):
        """Copy easytest agent scripts to newly created directory on target servers """

        print('Start to deploy agent scripts')
        agent_dir = path.join(EnvMgr._SERVER_DIR_, 'easytest_agent')
        agent_utils_dir = path.join(EnvMgr._SERVER_DIR_, 'easytest_agent/utils')
        if path.isdir(agent_dir):
            print('Agent scripts already exist')
            return agent_utils_dir

        mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP \
                | stat.S_IROTH | stat.S_IXOTH)
        for server in servers:
            with SftpClient(server=server, username=username,
                            password=password) as sftp:
                sftp.mkdir(agent_dir)
                sftp.mkdir(agent_utils_dir)
                regex = path.join(path.dirname(__name__), '**/*.*')
                for localf in glob.glob(regex, recursive=True):
                    if '__pycache__' not in localf:
                        remotef = path.join(agent_utils_dir, path.basename(localf))
                        print('\tcopy {} to {}:{}'.format(localf, server, remotef))
                        sftp.put(localf, remotef)
                        sftp.chmod(remotef, mode)

                sftp.rename(path.join(agent_utils_dir, 'remoterun.py'),
                            path.join(agent_dir, 'remoterun.py'))

        return agent_utils_dir

    @staticmethod
    def deploy_tests(test_files, servers, username='stephenw',
                     password='ca$hc0w'):
        """Copy test scripts to newly created directory on target servers """

        print('Start to deploy test scripts')
        remote_dir = path.join(EnvMgr._SERVER_DIR_,
                               EnvMgr.get_unique_name())
        mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP \
                | stat.S_IROTH | stat.S_IXOTH)
        for server in servers:
            with SftpClient(server=server, username=username,
                            password=password) as sftp:
                print('\tCopy {} to {}:{}'.format(test_files, server, remote_dir))
                sftp.mkdir(remote_dir)
                for localf in test_files:
                    remotef = path.join(remote_dir, path.basename(localf))
                    sftp.put(localf, remotef)
                    sftp.chmod(remotef, mode)

        return remote_dir
