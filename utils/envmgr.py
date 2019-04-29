#!/usr/bin/python3

import glob
import logging
import os
from os import path
import random
import stat
import string

from .ssh import SftpClient
from .logger import get_logger


logger = get_logger('EnvMgr', level=logging.DEBUG)


class EnvMgr(object):
    """Util class for deploying tests to test machines. """

    _SERVER_DIR_ = "/local"

    def __init__(self, servers, username, password, server_dir=None):
        self.servers = servers
        self.username = username
        self.password = password
        if server_dir is None:
            self.server_dir = EnvMgr._SERVER_DIR
        else:
            self.server_dir = server_dir

    @staticmethod
    def get_unique_name(prefix='test_'):
        chars = ''.join([random.choice(string.ascii_lowercase) \
                         for _ in range(8)])
        nums = ''.join([str(random.randint(0,9)) for _ in range(4)])
        return ''.join([prefix, chars, nums])

    def deploy_agents(self):
        """Copy easytest agent scripts to newly created directory on target
        servers.
        """

        logger.info('Start to deploy agent scripts')
        agent_dir = path.join(self.server_dir, 'easytest_agent')
        agent_utils_dir = path.join(self.server_dir, 'easytest_agent/utils')

        mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP \
                | stat.S_IROTH | stat.S_IXOTH)
        for server in self.servers:
            with SftpClient(server=server, username=self.username,
                            password=self.password) as sftp:
                # Create agent directory if necessary
                try:
                    sftp.listdir(agent_dir)
                    logger.info('Agent scripts already exist on %s', server)
                    continue
                except Exception:
                    sftp.mkdir(agent_dir)
                    sftp.mkdir(agent_utils_dir)

                regex = path.join(path.dirname(__name__), 'utils', '**/*.*')
                for localf in glob.glob(regex, recursive=True):
                    if '__pycache__' not in localf:
                        remotef = path.join(agent_utils_dir,
                                            path.basename(localf))
                        logger.info('Copy %s to %s:%s', localf, server, remotef)
                        sftp.put(localf, remotef)
                        sftp.chmod(remotef, mode)

                sftp.rename(path.join(agent_utils_dir, 'remoterun.py'),
                            path.join(agent_dir, 'remoterun.py'))

                # deploy config file
                local_conf = path.join(path.dirname(path.abspath(__name__)),
                                                    'config.ini')
                remote_conf = path.join(agent_dir, 'config.ini')
                logger.info('Copy %s to %s:%s', local_conf, server, remote_conf)
                sftp.put(local_conf, remote_conf)
                sftp.chmod(remote_conf, mode)

        return agent_dir

    def deploy_tests(self, test_files):
        """Copy test scripts to newly created directory on target servers """

        logger.info('Start to deploy test scripts')

        if not test_files:
            logger.warning('No tests need to be deployed')
            return

        local_bin_dir = path.join(path.dirname(test_files[0]), 'bin')
        remote_dir = path.join(self.server_dir, EnvMgr.get_unique_name())
        remote_scripts_dir = path.join(remote_dir, 'scripts')
        remote_bin_dir = path.join(remote_scripts_dir, 'bin')
        mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP \
                | stat.S_IROTH | stat.S_IXOTH)
        for server in self.servers:
            with SftpClient(server=server, username=self.username,
                            password=self.password) as sftp:
                sftp.mkdir(remote_dir)
                sftp.mkdir(remote_scripts_dir)
                sftp.mkdir(remote_bin_dir)

                for localf in test_files:
                    remotef = path.join(remote_scripts_dir, path.basename(localf))
                    logger.debug('Copy %s to %s:%s', localf, server, remotef)
                    sftp.put(localf, remotef)
                    sftp.chmod(remotef, mode)

                search_path = path.join(local_bin_dir, '**/*')
                logger.debug('Copy binaries used by test scripts: %s', search_path)
                for localf in glob.glob(search_path, recursive=True):
                    remotef = path.join(remote_bin_dir, path.basename(localf))
                    logger.debug('Copy %s to %s:%s', localf, server, remotef)
                    sftp.put(localf, remotef)
                    sftp.chmod(remotef, mode)

        return remote_dir

    def download(self, server_file):
        """Download server file"""

        local_dir = path.join('/tmp', EnvMgr.get_unique_name())
        if not path.isdir(local_dir):
            os.makedirs(local_dir)

        server, remote_file = server_file.split(':')
        local_file = path.join(local_dir, path.basename(server_file))
        logger.info('Download %s to %s', server_file, local_file)

        with SftpClient(server=server, username=self.username,
                        password=self.password) as sftp:
            sftp.get(remote_file, local_file)

        return local_file
