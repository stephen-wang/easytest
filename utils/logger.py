#!/usr/bin/python3

import logging
import os
from os import path


log_dir = path.join(path.dirname(path.dirname(__file__)), 'log')
log_file = path.join(log_dir, 'easytest.log')
agent_log_file = path.join(log_dir, 'easytest_agent.log')
root_logger = None


def get_logger(module_name, level=logging.DEBUG, is_agent=False):
    """Create and return logger object. Separate log files will be used for
    easytest and its daemon.
    """
    
    # Create root logger and setup log file/log level/formatter
    global root_logger
    if root_logger is None:
        if not path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        if is_agent:
            fh = logging.FileHandler(agent_log_file)
        else:
            fh = logging.FileHandler(log_file)

        fmt_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(fmt_str)
        fh.setFormatter(formatter)
        fh.setLevel(logging.DEBUG)

        root_logger = logging.getLogger('')
        root_logger.addHandler(fh)

    logger = logging.getLogger(module_name)
    logger.setLevel(level)
    return logger
