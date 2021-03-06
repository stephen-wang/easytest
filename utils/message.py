#!/usr/bin/python3

import random
import time


class Message(object):
    def __init__(self):
        self.val = None

    def __str__(self):
        return self.val.decode()

    @staticmethod
    def build_msg(**kargs):
        msg = ''
        for k, v in kargs.items():
            msg += '{} {}\n'.format(k, v)
        return bytes(msg, 'utf-8')

    @staticmethod
    def parse_msg(msg):
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8')

        if '\n' not in msg or ' ' not in msg:
            return None

        kvs = msg.split('\n')
        args = {}
        for k_v in kvs:
            if len(k_v) > 2:
               k, v = k_v.split(' ')
               args[k] = v

        return args


class SyncMsg(Message):
    """Sync-up message between easytest agent and aemon"""

    _MSG_INITIALIZED_ = False
    _MSGID_ = 0 

    def __init__(self, script, status, final_msg=False, msgid=None,
                 support_bundle=None):
        self.script = script
        self.status = status
        self.final_msg = final_msg
        self.msgid = self.get_msgid() if msgid is None else msgid
        self.support_bundle = support_bundle
        self.val = self.build_msg(sync=self.msgid, script=script, status=status,
                                  support_bundle=support_bundle)

    @classmethod
    def get_msgid(cls):
        if not cls._MSG_INITIALIZED_:
            cls._MSG_INITIALIZED_ = True
            random.seed(time.time())
            cls._MSGID_ = random.randint(5000, 50000)

        cls._MSGID_ += 1
        return cls._MSGID_

    @classmethod
    def from_msg(cls, msg):
        final_msg = False 
        content = Message.parse_msg(msg)
        if content['script'] == 'all' and content['status'] == 'Finished':
            final_msg = True

        return cls(msgid=content['sync'], script=content['script'],
                   status=content['status'], final_msg=final_msg,
                   support_bundle=content['support_bundle'])


class AckMsg(Message):
    """Response to SyncMsg"""

    def __init__(self, msgid):
        self.val = self.build_msg(ack=msgid)
