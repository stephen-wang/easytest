#!/usr/bin/python3


from enum import Enum
import logging
from os import path

from .exceptions import IllegalResultError
from .message import SyncMsg, AckMsg
from .logger import get_logger


logger = get_logger('ResultMgr', level=logging.DEBUG)


class TestResult(Enum):
    ABORTED = 'Aborted'
    FAILED = 'Failed'
    FINISHED = 'Finished'
    NOTRUN = 'NotRun'
    RUNNING = 'Running'
    SKIPPED = 'Skipped'


class ResultMgr(object):

    def __init__(self, testcases, progress_mgr):
        self.tests_done = False
        self.progress_mgr = progress_mgr 

        self.results = {}
        for testcase in testcases:
            script = testcase.relpath
            self.results[script] = testcase.result

    def sync_result(self, server, chan, msg):
        logger.debug('Receive sync update from %s: %s', chan.getpeername(),
                     msg.decode())
        sync = SyncMsg.from_msg(msg)
        tests_done = False
        if sync.final_msg:
            self.progress_mgr.print_prompt('\n\t{}\n'.format(self.info()))
            tests_done = True 
        else:
            self.update(sync.script, sync.status)

        ack = AckMsg(sync.msgid)
        server.response_msg(chan, ack.val)
        self.tests_done = tests_done

    def update(self, script, status):
        if not isinstance(status,  TestResult):
            try:
                status = TestResult(status)
            except Exception:
                error = 'Set result of {} to {}'.format(script, status)
                raise IllegalResultError(error)
        
        if script in self.results:
            self.results[script] = status
            self.progress_mgr.update_test_status(script, status)

    def count(self, status):
        return sum([1 for v in self.results.values() if v == status])

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
        info_fmt = 'Total {}, passed {}, skipped {}, failed {}, aborted {}, '\
                   + 'not_run {}'
        return info_fmt.format(self.total(), self.passed(), self.skipped(),
                               self.failed(), self.aborted(), self.not_run())
