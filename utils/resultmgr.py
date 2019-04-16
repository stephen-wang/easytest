#!/usr/bin/python3


from os import path

from .exceptions import IllegalResultError
from .message import SyncMsg, AckMsg


class TestResult:
    ABORTED = 'Aborted'
    FAILED = 'Failed'
    FINISHED = 'Finished'
    NOTRUN = 'NotRun'
    RUNNING = 'Running'


class ResultMgr(object):

    _ALLOWED_RESULTS_ = [TestResult.ABORTED, TestResult.FAILED,
                         TestResult.FINISHED, TestResult.NOTRUN,
                         TestResult.RUNNING]

    def __init__(self, testcases):
        self.results = {}
        for testcase in testcases:
            script = path.basename(testcase.script)
            self.results[script] = testcase.result

    def sync_result(self, server, chan, msg):
        sync = SyncMsg.from_msg(msg)
        if not sync.final_msg:
            self.update(path.basename(sync.script), sync.status)

        ack = AckMsg(sync.msgid)
        server.response_msg(chan, ack.val)

    def update(self, script, status):
        if status not in ResultMgr._ALLOWED_RESULTS_:
            error = 'Set result of {} to {}'.format(script, status)
            raise IllegalResultError(error)
        
        if script in self.results:
            self.results[script] = status

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

    def info(self):
        info_fmt = 'total {}, passed {}, failed {}, aborted {}'
        return info_fmt.format(self.total(), self.passed(),
                               self.failed(), self.aborted())
