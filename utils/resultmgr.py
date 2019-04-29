#!/usr/bin/python3


from enum import Enum
import logging
import os
from os import path
import tarfile

from .exceptions import IllegalResultError
from .message import SyncMsg, AckMsg
from .logger import get_logger


logger = get_logger('ResultMgr', level=logging.DEBUG)


def make_tarfile(output_file, src_dir):
    """Create tar.gz file 'output_file' from 'src_dir' """
    with tarfile.open(output_file, 'w:gz') as tar:
        tar.add(src_dir, arcname=os.path.basename(src_dir))


class TestResult(Enum):
    ABORTED = 'Aborted'
    FAILED = 'Failed'
    FINISHED = 'Finished'
    NOTRUN = 'NotRun'
    RUNNING = 'Running'
    SKIPPED = 'Skipped'


class ResultMgr(object):
    """Util class for managing status update of test cases."""

    def __init__(self, testcases, term_mgr, env_mgr):
        self.tests_done = False
        self.term_mgr = term_mgr 
        self.env_mgr = env_mgr

        self.results = {}
        for testcase in testcases:
            self.results[testcase.relpath] = testcase

    def sync_skipped_tests(self):
        """Some tests belong to requested group but are marked as 'disabled',
        this function is to mark and show the results of those tests as
        'SKIPPED'.
        """

        logger.debug('Sync-up skipped tests')
        for test_rel_path, testcase in self.results.items():
            if testcase.result == TestResult.SKIPPED:
                self.update(test_rel_path, testcase.result)
        
    def sync_result(self, server, chan, msg):
        """Response to test progress sync-up requests from easytest agent."""

        sync = SyncMsg.from_msg(msg)
        logger.debug('Receive sync update from %s: %s', chan.getpeername(), str(sync))
        tests_done = False
        if sync.final_msg:
            tests_done = True 
        else:
            self.update(sync.script, sync.status,
                        remote_support_bundle=sync.support_bundle)

        ack = AckMsg(sync.msgid)
        server.response_msg(chan, ack.val)
        self.tests_done = tests_done

    def update(self, script, status, remote_support_bundle=None):
        """Update test result to terminal"""

        if not isinstance(status,  TestResult):
            try:
                status = TestResult(status)
            except Exception:
                error = 'Set result of {} to {}'.format(script, status)
                raise IllegalResultError(error)
        
        test = self.results[script]
        if script in self.results:
            test.result = status
            if status == TestResult.FAILED:
                if remote_support_bundle is not None:
                    test.remote_failure_pack = remote_support_bundle
                    try:
                        test.local_failure_pack = \
                            self.env_mgr.download(remote_support_bundle)
                    except Exception as e:
                        logger.warning('Can\'t download %s: %s',
                                       remote_support_bundle, str(e))

            self.term_mgr.update_test_status(script, status,
                                             test.local_failure_pack)

    def count(self, status):
        return sum([1 for t in self.results.values() if t.result == status])

    def total(self):
        return len(self.results)

    def aborted(self): 
        return self.count(TestResult.ABORTED)

    def failed(self): 
        return self.count(TestResult.FAILED)

    def not_run(self):
        return self.count(TestResult.NOTRUN)

    def passed(self):
        return self.count(TestResult.FINISHED)

    def running(self):
        return self.count(TestResult.RUNNING)

    def skipped(self):
        return self.count(TestResult.SKIPPED)

    def info(self):
        """Make statistics info of test result printable"""

        info_fmt = 'Total {}, passed {}, skipped {}, failed {}, aborted {}, '\
                   + 'not_run {}'
        return info_fmt.format(self.total(), self.passed(), self.skipped(),
                               self.failed(), self.aborted(), self.not_run())
