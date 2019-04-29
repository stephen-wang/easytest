#!/usr/bin/python3

import glob
import logging
from os import path
import re
import sys

from .resultmgr import TestResult
from .exceptions import MalformedScriptError
from .logger import get_logger


TEST_GROUP_ENABLED = 'enabled' 
TEST_GROUP_DISABLED = 'disabled' 
logger = get_logger('TestsetMgr', level=logging.DEBUG)


class TestCase:
    """ Util class for storing charateristics of each test script. """

    def __init__(self, abspath, relpath):
        self.abspath = abspath
        self.relpath = relpath
        self.groups = [] 
        self.disabled_groups = []
        self.parallel = False 
        self.result = TestResult.NOTRUN 

        # Support bundle (contains log and potential coredump) of failed test
        self.remote_failure_pack = None
        self.local_failure_pack = None

    def add_group(self, group):
        self.groups.append(group)

    def add_disabled_group(self, group):
        self.disabled_groups.append(group)

    def set_parallel(self, parallel):
        self.parallel = parallel

    def set_result(self, result):
        self.result = result

    def __str__(self):
        fmt = ('Testcase:\n\tabspath {}\n\trelpath {}\n\tgroups {}\n\t'
               'disabled groups {}\n\tparalle {}\n\tresult {}')
        return fmt.format(self.abspath, self.relpath, self.groups,
                          self.disabled_groups, self.parallel, self.result)


class TestsetMgr(object):
    """The util class for collecting tests to be run per user input"""

    _TEST_ROOT_ = path.join(path.abspath(path.dirname(__file__)), '../tests')

    @staticmethod
    def get_test_fullpath(relpath):
        return path.normpath(path.join(TestsetMgr._TEST_ROOT_, relpath))


    @staticmethod
    def get_tests(req_tests, req_groups):
        """ Search under directory 'test_root' and return all test scripts
        belonging to groups 'req_groups'
        """

        logger.info('Collect test scripts...')
        tests = []
        if req_tests:
            # Get tests from script(s) explicitly specified by user
            for test in req_tests:
                 test_script = TestsetMgr.get_test_fullpath(test)
                 testcase = TestsetMgr.get_testcase(test_script)
                 if set(req_groups).issubset(set(testcase.groups)):
                     tests.append(testcase)
        else:
            # Get tests from group(s) explicitly specified by user
            test_path_wildcard = path.join(TestsetMgr._TEST_ROOT_, '**/*.*')
            for test_script in glob.glob(test_path_wildcard, recursive=True):
                testcase = TestsetMgr.get_testcase(path.normpath(test_script))
                for group in set(req_groups):
                    if group in testcase.groups:
                        tests.append(testcase)
                        break

                if testcase not in tests:
                    for group in set(req_groups):
                        if group in testcase.disabled_groups:
                            testcase.set_result(TestResult.SKIPPED)
                            tests.append(testcase)
                            break

        logger.info('Found tests: %s', str([test.relpath for test in tests]))
        return tests

    @staticmethod
    def get_testcase(test_script):
        """Parse test script and get group list to which the test belongs and
        parallelism state.

        Note: 1) a test can belong to one or multiple groups by below
                 declarations:
                        #group-A : enabled
                        #group-B : enabled
                        #group-C : disabled
                
                 Above statments make the test belong to group 'A', 'B', 'C' at
                 same time, but the test is disabled in group 'C'.

              2) A test can declare to be parallel or not by below statement:
                       #parallel : true  #or false
        """

        logger.debug('Check script %s', test_script)

        # Set patterns for parsing group and parallel properties
        regex_group = re.compile('#group-(.*)(\s*):(\s*)(.+)')
        regex_parallel = re.compile('#parallel(\s*):(\s*)(.+)')

        # Check test script line by line
        relpath = path.relpath(test_script, TestsetMgr._TEST_ROOT_)
        testcase= TestCase(test_script, relpath)
        with open(test_script) as f:
            set_parallel = False
            for line in f:
                # Parse groups
                if line.startswith('#group-'):
                    m = regex_group.match(line)
                    if m:
                        group = m.group(1).strip()
                        state = m.group(4).strip()
                        if state == TEST_GROUP_ENABLED:
                            testcase.add_group(group)
                        elif state == TEST_GROUP_DISABLED:
                            testcase.add_disabled_group(group)
                    else:
                        msg = 'Error: "{}" in {}'.format(line, test_script)
                        raise MalformedScriptError(msg)

                # Parse parallelism, we should do this at most once
                elif line.startswith('#parallel'):
                    if set_parallel:
                        msgFmt = 'More than one "#parallel: xxx" exist in {}'
                        raise MalformedScriptError(msgFmt.format(test_script))

                    set_parallel = True
                    m = regex_parallel.match(line)
                    if m:
                        parallel_run = (m.group(3).strip().tolower() == 'true')
                        testcase.set_parallel(parallel_run)
        logger.debug(str(testcase))
        return testcase


if __name__ == "__main__": 
    if len(sys.argv) != 2:
        print('Usage: {} [testcript]'.format(sys.argv[0]))
        sys.exit(-1)

    testcase = TestsetMgr.get_testcase(TestsetMgr.get_test_fullpath(sys.argv[1]))
    logger.info('Test: %s', testcase.abspath)
    logger.info('relpath: %s', testcase.relpath)
    logger.info('Parallel: %s', testcase.parallel)
    logger.info('Groups: %s', testcase.groups)
    logger.info('Result: %s', testcase.result)
