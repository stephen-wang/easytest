#!/usr/bin/python3 

from enum import Enum
import os
import re
import sys
import termios
import tty


class TextColor(Enum):
    NONE = "\033[0m"
    RED = "\033[0;31m"
    BLACK = "\033[0;30m"
    WHITE = "\033[1;37m"
    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    YELLOW = "\033[1;33m"
    BROWN = "\033[0;33m"
    CYAN = "\033[0;36m"
    PURPLE = "\033[0;35m"
    DARK_GRAY = "\033[1;30m"
    LIGHT_BLUE = "\033[1;34m"
    LIGHT_GREEN = "\033[1;32m"
    LIGHT_CYAN = "\033[1;36m"
    LIGHT_RED = "\033[1;31m"
    LIGHT_PURPLE = "\033[1;35m"
    LIGHT_GRAY = "\033[0;37m"


class TermOps:
    """Util class for terminal operations.
    """


    @staticmethod 
    def colored_text(color, text):
        """Enclose text the escaped characters so that text can be printed with
        requireed color.
        """

        if not isinstance(color, TextColor):
            raise Exception('Unsupported color {}'.format(color))

        return '{}{}{}'.format(color.value, text, TextColor.NONE.value)

    @staticmethod
    def get_cursor_pos():
        """Get row and column number of current cursor. """

        buf = ""
        stdin = sys.stdin.fileno()
        tattr = termios.tcgetattr(stdin)
        try:
            # Change stdin to cbbrea mode, the the cursor moves to new line
            # without pressing Entery key.
            tty.setcbreak(stdin, termios.TCSANOW)

            # Transmit the magic characters to get current cursor position
            sys.stdout.write("\x1b[6n")
            sys.stdout.flush()

            while True:
                buf += sys.stdin.read(1)
                if buf[-1] == "R":
                    break
        finally:
            # Restore stdin configuration
            termios.tcsetattr(stdin, termios.TCSANOW, tattr) 

        try:
            # The output of "\x1b[6n" would be like "\x1b[15;1R", we use below
            # regular express to parse out row/column number
            matches = re.match(r"^\x1b\[(\d*);(\d*)R", buf)
            groups = matches.groups()
        except AttributeError:
            return None, None

        return (int(groups[0]), int(groups[1]))

    @staticmethod
    def disable_term_echo():
        """Stop echoing on stdin when pressing keyboard. """

        fd = sys.stdin.fileno()
        oldattr = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSADRAIN, newattr)
        return oldattr

    @staticmethod
    def enable_term_echo(attr):
        """Restore echoing on stdin when pressing keyboard, 'attr' is returned
        from disable_term_echo().
        """

        fd = sys.stdin.fileno()
        termios.tcsetattr(fd, termios.TCSADRAIN, attr)

    @staticmethod
    def hide_cursor():
        """Make terminal hide blinking cursor."""

        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    @staticmethod
    def show_cursor():
        """Make termnial show blinking cursor."""

        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    @staticmethod
    def get_term_size():
        """Return maximum rows and columns of current terminal."""

        termsize = os.get_terminal_size()
        return termsize.lines, termsize.columns

    @staticmethod
    def print_at(x, y, msg, end=''):
        position = '\033[{};{}f'.format(x, y)
        override_chars = ' '*_MAX_COLS_ + '\r'
        print(position+override_chars+msg, end=end)


_MAX_ROWS_, _MAX_COLS_ = TermOps.get_term_size()

