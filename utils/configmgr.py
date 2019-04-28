#!/usr/bin/python3

import configparser
import logging
from os import path

from .exceptions import InvalidConfigError
from .logger import get_logger


logger = get_logger('ConfigMgr', level=logging.DEBUG)


class ConfigMgr:
    """Read and store config data needed for testing"""

    _CONFIG_FILE_ = path.join(path.dirname(__name__), 'config.ini')

    def __init__(self, config_file=None):
        """Initialize class members"""

        if config_file is None:
            config_file = ConfigMgr._CONFIG_FILE_
        self.config = self._read_config(config_file) 

        self.server_username = self.config.get('server', 'username')
        self.server_password = self.config.get('server', 'password')
        self.server_testdir = self.config.get('server', 'testdir')

        self.daemon_username = self.config.get('daemon', 'username')
        self.daemon_password = self.config.get('daemon', 'password')
        self.daemon_port = self.config.getint('daemon', 'port')

    def _read_config(self, cf):
        """Parse configuration file and return config object"""

        config = None
        try:
            config = configparser.ConfigParser()
            config.read(cf)
        except configparser.Error as e:
            msg = 'Invalid configure in {}'.format(cf)
            logger.info(msg)
            raise InvalidConfigError(msg)

        return config

    def __str__(self):
        fmt = 'server_username:{}, server_password:{}, server_testdir: {}, '\
              'daemon_usernmae:{}, daemon_password:{}, daemon_port:{}'
        return fmt.format(self.server_username, self.server_password,
                          self.server_testdir, self.daemon_username,
                          self.daemon_password, self.daemon_port)
