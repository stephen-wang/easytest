#!/usr/bin/python3

import random
import time


class Message(object):
    @staticmethod
    def msg_from_fields(**kargs):
        msg = ''
        for k, v in kargs.items():
            msg += '{} {}\n'.format(k, v)
        return bytes(msg, 'utf-8')

    @staticmethod
    def parse_msg(msg):
        kvs = msg.decode('utf-8').split('\n')
        args = {}
        for k_v in kvs:
            k, v = kvs.split(' ')
            args[k] = v

        return args

class SyncMsg(Message):

    _MSG_INITIALIZED_ = False
    _MSGID_ = 0 

    def __init__(self, script, status):
        self.msgid = self.get_msgid()
        self.val = self.msg_from_fields(sync=self.msgid, script=script,
                                        status=status)
    @classmethod
    def get_msgid(cls):
        if not cls._MSG_INITIALIZED_:
            cls._MSG_INITIALIZED_ = True
            random.seed(time.time())
            cls._MSGID_ = random.randint(5000, 50000)

        cls._MSGID_ += 1
        return cls._MSGID_

    @staticmethod
    def ack_msg(chan, msg):
        final_msg = False
        sync_info = Message.parse_msg(msg)['sync']

        if sync_info and 'sync' in sync_info and 'script' in sync_info \
            and 'status' in sync_info:

            msgid = sync_info['sync']
            ack = AckMsg(msgid)
            chan.send(ack.val)
            print('Recevie sync msg: ', msg)

            if sync_info['script'] == 'all' and sync_info['status'] == 'Done':
                final_msg = True

            return ack.val, final_sync
        else:
            print('Invalid sync msg [{}], ignored!'.format(msg))
            return None, final_msg
            


class AckMsg(Message):
    def __init__(self, msgid):
        self.val = self.msg_from_fields(ack=msgid)
