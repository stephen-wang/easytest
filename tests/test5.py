#!/usr/bin/python3

#group-C13 : enabled

from os import path
import subprocess
import sys


if __name__ == '__main__':

    ret = 0
    out_file = 'test.out'
    cmd = path.join(path.abspath(path.dirname(__file__)), 'bin', 'divideby0')
    try:
        subprocess.check_call([cmd], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        ret = -1
        msg = 'Cmd: {}\nErrCode: {}\nMsg: {}\n'.format(cmd, e.returncode, str(e))
        with open(out_file, 'w') as f:
            f.write(msg)
    finally:
        sys.exit(ret)
