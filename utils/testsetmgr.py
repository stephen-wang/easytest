#!/usr/bin/python3

import glob
from os import path
import re
import sys

from .exceptions import MalformedScriptError


TEST_GROUP_ENABLED = 'enabled' 
TEST_GROUP_DISABLED = 'disabled' 


class Testcase:
    """ Util class for storing charateristics of each test script. """

    def __init__(self, filepath, groups=[], parallel=False, result='NotRun'):
        self.script = filepath 
        self.groups = groups
        self.parallel = parallel 
        self.result = result 

    def addGroup(self, group):
        self.groups.append(group)

    def setParallel(self, parallel):
        self.parallel = parallel


class TestsetMgr(object):
    """The util class for collecting tests to be run per user input"""

    __TEST_ROOT__ = path.join(path.abspath(path.dirname(__file__)), '../tests')

    @staticmethod
    def get_test_fullpath(relpath):
        return path.normpath(path.join(TestsetMgr.__TEST_ROOT__, relpath))


    @staticmethod
    def get_tests(req_tests, req_groups):
        """ Search under directory 'test_root' and return all test scripts
        belonging to groups 'req_groups'
        """

        tests = []
        if req_tests:
            # Get tests from script(s) explicitly specified by user
            for test in req_tests:
                 test_script = TestsetMgr.get_test_fullpath(test)
                 testcase = TestsetMgr.get_testcase(test_script)
                 if set(testcase.groups) - set(req_groups):
                     tests.append(testcase)
        else:
            # Get tests from group(s) explicitly specified by user
            test_path_wildcard = path.join(TestsetMgr.__TEST_ROOT__, '**/*.*')
            for test_script in glob.glob(test_path_wildcard, recursive=True):
                testcase = TestsetMgr.get_testcase(path.normpath(test_script))
                if set(testcase.groups) - set(req_groups):
                    tests.append(testcase)

        print('Tests to be run: ', [test.script for test in tests])
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
                
                 Above statments make the test belong to group 'A', 'B', 'C'at
                 same time, but the test is disabled in group 'C'.

              2) A test can declare to be parallel or not by below statement:
                       #parallel : true  #or false
        """

        # Set patterns for parsing group and parallel properties
        regex_group = re.compile('#group-(.*)(\s*):(\s*)(.+)')
        regex_parallel = re.compile('#parallel(\s*):(\s*)(.+)')

        # Check test script line by line
        testcase= Testcase(test_script)
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
                            testcase.addGroup(group)
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

        return testcase


if __name__ == "__main__": 
    if len(sys.argv) != 2:
        print('Usage: {} [testcript]'.format(sys.argv[0]))
        sys.exit(-1)

    testcase = TestsetMgr.get_testcase(TestsetMgr.get_test_fullpath(sys.argv[1]))
    print('Test: ', testcase.script)
    print('Parallel: ', testcase.parallel)
    print('Groups: ', testcase.groups)
    print('Result: ', testcase.result)
