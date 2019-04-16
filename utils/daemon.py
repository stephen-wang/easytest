#!/usr/bin/python3

from .paramiko import RSAKey
from .paramiko.server import ServerInterface
import socket


class Daemon(ServerInterface):
    def __init__(self, server, port):
        self.server = server
        self.port = port
        self.server_key = RSAKey.generate(2048)
        self.listensock = None
        self.transport = None
        self.chans = set()

    def start(self):
        self.listensock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listensock.bind((self.server, self.port))
        self.listensock.listen(5)
        t = threading.Thread(target=self.handle_requests)
        t.setDaemon(True)
        t.start()

    def handle_requests(self):
        self.manage_sessions()
        while True:
            try:
                conn, addr = self.listensock.accept()
                if not conn:
                    break
            except Exception e:
                break

            transport = paramiko.Transport(conn) 
            transport.add_server_key(self.server_key)
            t2 = threading.Thread(target=self.transportthread, args=(transport))
            t2.setDaemon(True)
            t2.start()

    def transportthread(self, transport):
        while transport.is_active():
            chan = transport.accept()
            if chan is None:
                break 
            self.chans.append(chan)

    def manage_sessions(self):
        while True:
            if not self.chans:
                time.sleep(1)
                continue

            i = 0
            while i < len(self.chans):
                if self.chans[i].recv_ready():
                    msg = self.chans[i].recv(2048)
                    self.ack_message(self.chans[i], msg)
                    if self.test_done(msg):
                        self.chans.pop(i)
                    else:
                        i += 1

    def test_done(self, msg):
        if msg.strip() == 'Test Done':
            return True
        else:
            return False

    def ack_message(self, chan, msg):
        if self.tets_done(msg):
            chan.send('Ack\n')
            chan.close()
        else:
            regex = re.compile('Test finished\nScript:(.*)\nStatus:(.*)\nError:(.*)\n')
            m = re.match(regex, msg)
            if m:
                script = m.group(1).strip()
                status = m.group(2).strip()
                error = m.group(3).strip()
                # how to update test state
                chan.send('Ack\n')
            else:
                print('Invalid message {} from xxx, ignore'.format(msg))

    def check_allowed_auths(username):
        if username == 'easytestagent':
            return 'password'
        else:
            return 'none'

    def check_aut_password(username, password):
        if username == 'easytestagent' and password == 'syncme':
            return paramiko.AUTH_SUCCESSFUL
        else:
            return paramiko.AUTH_FAILED
