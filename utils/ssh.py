#!/usr/bin/python3

import logging
import paramiko
import re
import socket
import threading
import time

from .message import AckMsg
from .logger import get_logger


class SftpClient(object):
    def __init__(self, server, username, password, port=22):
        self.server= server
        self.port = port
        self.username = username
        self.password = password
        self.sftp = None
        self.logger = get_logger('SftpClient', level=logging.DEBUG)

    def open_session(self):
        t = paramiko.Transport((self.server, self.port))
        t.connect(username=self.username, password=self.password)
        return paramiko.SFTPClient.from_transport(t)

    def __enter__(self):
        self.logger.debug('Start sftp session to %s', self.server)
        self.sftp = self.open_session()
        return self.sftp

    def __exit__(self, exc_type, exc_val, exc_tb): 
        self.logger.debug('sftp session is disconnected from %s', self.server)
        self.sftp.close() 


class SSHClient:
    def __init__(self, server, username, password, port=22):
        self.server = server
        self.port = port
        self.username = username
        self.password =  password
        self.client = None
        self.logger = get_logger('SSHClient', level=logging.DEBUG)

    def __enter__(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        self.client.connect(self.server, port=self.port, username=self.username,
                            password=self.password, timeout=5)
        self.logger.debug('Connected to %s:%d', self.server, self.port)
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
        self.logger.debug('Disconnected from %s:%s', self.server, self.port)


class SSHConnector(object):
    _MAX_MSG_SIZE_ = 2048

    def __init__(self, server, username, password, port=22):
        self.server = server
        self.port = port 
        self.username = username
        self.password = password
        self.transport = None
        self.chan = None
        self.logger = get_logger('SSHConnector', level=logging.DEBUG)

    def connect(self):
        self.logger.debug('Connect to %s:%d', self.server, self.port)
        try:
            self.transport = paramiko.Transport((self.server, self.port))
            self.transport.connect(username=self.username,
                                   password=self.password)
            self.chan = self.transport.open_channel('session')
        except Exception as e:
            raise Exception('Failed to connect server:{}'.format(str(e)))
        self.logger.debug('Server is connected')


    def close(self):
        if self.transport and self.ransport.is_active():
            self.transport.close()
        self.logger.info('Disconnected from %s:%d', self.server, self.port)

    def send(self, msg):
        if self.chan and self.chan.send_ready():
            self.chan.send(msg)

    def recv(self):
        if self.chan:
            msg = self.chan.recv(SSHConnector._MAX_MSG_SIZE_)
            return msg
        return None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb): 
        self.close()
        self.logger.debug('Disconnected from %s:%s', self.server, self.port)


class SSHServer(paramiko.server.ServerInterface):

    _MAX_MSG_SIZE_ = 2048 

    def __init__(self, msg_handler, username, password, port=17258):
        self.msg_handler = msg_handler
        self.username = username
        self.password = password
        self.port = port 
        self.server_key = paramiko.RSAKey.generate(self._MAX_MSG_SIZE_)
        self.sock_thread = None
        self.chan_thread = None
        self.chans = {} 
        self.chan_lock = threading.Lock()
        self._exit = False
        self.logger = get_logger('SSHServer', level=logging.DEBUG)

    def execute(self):
        self.sock_thread = threading.Thread(target=self.handle_connect_req)
        self.sock_thread.setDaemon(True)
        self.sock_thread.start()

        self.chan_thread = threading.Thread(target=self.process_msg)
        self.chan_thread.setDaemon(True)
        self.chan_thread.start()

        self.logger.info('Server is listening on *.*:{}'.format(self.port))
        self.sock_thread.join()
        self.chan_thread.join()
        self.logger.info('Server is stopped'.format(self.port))

    def stop(self):
        self._exit = True

    def response_msg(self, chan, msg):
        if chan and chan.send_ready():
            chan.send(msg)

    def process_msg(self):
        while True:
            need_sleep = True 
            self.chan_lock.acquire()
            for transport in list(self.chans.keys()):
                if not transport.is_active():
                    self.chans.pop(transport)
                    continue
                
                chan = self.chans[transport]
                if chan and chan.recv_ready():
                    msg = chan.recv(self._MAX_MSG_SIZE_)
                    self.msg_handler(self, chan, msg)
                    need_sleep = False

            self.chan_lock.release()

            if self._exit:
                break

            if need_sleep:
                time.sleep(1)

        # Close all active tranports/channels
        self.chan_lock.acquire()
        for transport in list(self.chans.keys()):
            if transport and transport.is_active():
                transport.close()
            del self.chans[transport]

    def handle_connect_req(self):
        listensock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listensock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listensock.bind(('', self.port))
        listensock.listen(5)

        listensock.settimeout(1)
        while True:
            try:
                connsock, addr = listensock.accept()
            except socket.timeout:
                if self._exit:
                    break
                else:
                    continue 
            except Exception as e:
                break

            transport = paramiko.transport.Transport(connsock)
            transport.add_server_key(self.server_key)
            transport.start_server(server=self)

            chan = transport.accept()
            self.chan_lock.acquire()
            self.chans[transport] = chan
            self.chan_lock.release()

        listensock.close()


    def check_allowed_auths(self, username):
        if username == self._DEFAULT_USERNAME_:
            return 'password'

        return 'none'

    def check_auth_password(self, username, password):
        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL
        else:
            return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def enable_auth_gssapi(self):
        return False

    def get_banner(self):
        return 'easytest daemon', 'en' 
