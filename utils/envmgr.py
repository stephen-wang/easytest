#!/usr/bin/python3

import glob
import logging
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

    @staticmethod
    def get_unique_name(prefix='test_'):
        chars = ''.join([random.choice(string.ascii_lowercase) \
                         for _ in range(8)])
        nums = ''.join([str(random.randint(0,9)) for _ in range(4)])
        return ''.join([prefix, chars, nums])

    @staticmethod
    def deploy_agents(servers, username='stephenw', password='l0ve2o19'):
        """Copy easytest agent scripts to newly created directory on target servers """

        logger.info('Start to deploy agent scripts')
        agent_dir = path.join(EnvMgr._SERVER_DIR_, 'easytest_agent')
        agent_utils_dir = path.join(EnvMgr._SERVER_DIR_, 'easytest_agent/utils')

        mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP \
                | stat.S_IROTH | stat.S_IXOTH)
        for server in servers:
            with SftpClient(server=server, username=username,
                            password=password) as sftp:
                # Create agent directory if necessary
                try:
                    sftp.listdir(agent_dir)
                    logger.info('Agent scripts already exist on %s', server)
                    continue
                except Exception:
                    sftp.mkdir(agent_dir)
                    sftp.mkdir(agent_utils_dir)

                regex = path.join(path.dirname(__name__), '**/*.*')
                for localf in glob.glob(regex, recursive=True):
                    if '__pycache__' not in localf:
                        remotef = path.join(agent_utils_dir,
                                            path.basename(localf))
                        logger.info('Copy %s to %s:%s', localf, server, remotef)
                        sftp.put(localf, remotef)
                        sftp.chmod(remotef, mode)

                sftp.rename(path.join(agent_utils_dir, 'remoterun.py'),
                            path.join(agent_dir, 'remoterun.py'))

        return agent_dir

    @staticmethod
    def deploy_tests(test_files, servers, username='stephenw',
                     password='l0ve2o19'):
        """Copy test scripts to newly created directory on target servers """

        logger.info('Start to deploy test scripts')
        remote_dir = path.join(EnvMgr._SERVER_DIR_,
                               EnvMgr.get_unique_name())
        mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP \
                | stat.S_IROTH | stat.S_IXOTH)
        for server in servers:
            with SftpClient(server=server, username=username,
                            password=password) as sftp:
                logger.debug('Copy %s to %s:%s', test_files, server, remote_dir)
                sftp.mkdir(remote_dir)
                for localf in test_files:
                    remotef = path.join(remote_dir, path.basename(localf))
                    sftp.put(localf, remotef)
                    sftp.chmod(remotef, mode)

        return remote_dir
