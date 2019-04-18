#!/usr/bin/python

import logging
import sys

from .logger import get_logger
from .resultmgr import TestResult
from .termops import TermOps, TextColor


logger = get_logger('ProgressMgr', level=logging.DEBUG)


class ProgressMgr:
    """The util class for updating test progress to console"""

    MAX_ROWS, MAX_COLS = TermOps.get_term_size()
    RESULT_COLOR_MAPS = {
        TestResult.FINISHED : TextColor.GREEN, 
        TestResult.SKIPPED: TextColor.DARK_GRAY, 
        TestResult.ABORTED: TextColor.RED, 
        TestResult.FAILED: TextColor.RED, 
        TestResult.RUNNING: TextColor.WHITE, 
        TestResult.NOTRUN: TextColor.LIGHT_GRAY, 
    }

    def __init__(self, rel_test_paths):
        """Initialze class members """

        # Save test script and the line number where it's printed out
        self.test_positions = dict()

        # The relative paths of all tests to be run, we don't need absolute path
        # because it's different between local and test machines
        self.rel_test_paths = rel_test_paths

        self.max_path_len = max([len(test_path) for test_path in self.rel_test_paths])
        self.term_attr = None
        self.cursor_pos = None

    @staticmethod
    def print_prompt(msg):
        """Print out some prompt message"""

        print(' '*120+'\r'+msg+'\r', end='')

    def set_term(self):
        """Prepare for terminal operations"""

        self.term_attr = TermOps.disable_term_echo()
        TermOps.hide_cursor()

    def restore_term(self):
        """Restore terminal configureation"""

        TermOps.enable_term_echo(self.term_attr)
        TermOps.show_cursor()

    def __enter__(self):
        self.set_term()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb): 
        self.restore_term()

    @classmethod
    def test_result_color(cls, test_result):
        """Get color that will be used for printing out specific test result"""

        return cls.RESULT_COLOR_MAPS[test_result]

    def formatted_path_str(self, test_path):
        """Format test script paths so that all of them occupy same witdth and
        align to left for graceful output.
        """

        fmt = '\t{0: >%d}' % self.max_path_len
        formatted_path = fmt.format(test_path) 
        return formatted_path

    def formatted_delimiter_str(self, test):
        """Format delimiter, just identify the number of '-'s """

        return ' ' + '-' * int(self.MAX_COLS/2 - self.max_path_len) + ' '

    def formatted_status_str(self, status):
        """Identify color of test status and format the output"""

        color = self.test_result_color(status)
        colored_status = TermOps.colored_text(color, status.value)
        return '[' + colored_status + ']'

    def formatted_test_status_str(self, test, status):
        """Construct and return formatted test status info like below:

               path/to/testscript1.py ------ [Running]
               path/to/testscript2.py ------ [Finished]
               path/to/testscript3.py ------ [Failed]
        """

        script_part = self.formatted_path_str(test)
        delim_part = self.formatted_delimiter_str(test)
        status_part = self.formatted_status_str(status)
        return script_part + delim_part + status_part

    def move_up_position(self):
        """Reduce the stored line number by 1 """

        for script in self.test_positions.keys():
            oldx, oldy = self.test_positions[script];
            self.test_positions[script] = (oldx-1, oldy)

    def print_test_status(self, test, status):
        """Format and output test status to terminal, the position (row & line)
        where the info will be printed is also saved for later update.
        """

        logger.debug('Print test status (%s, %s)', test, status)

        # Get the position where to print the test status
        x, y = TermOps.get_cursor_pos()

        # Save the position where to print the information
        self.test_positions[test] = (x, y)

        # Format and output tests status
        msg = self.formatted_test_status_str(test, status)
        TermOps.print_at(x, y, msg, end='\n') 

        # After every print, cursor moves to next line and saved positions
        # are moved one line up
        self.move_up_position()

        # Save current cursor position so that continue to print after updating
        # status
        self.save_cursor_pos()

    def update_test_status(self, test, status):
        """Update test status to terminal"""

        # Invalid script, ignore it
        if test not in self.rel_test_paths:
            return

        # It's the 1st status update, forward it to print_test_status()
        if test not in self.test_positions.keys():
            self.print_test_status(test, status)
            return

        # Get the position where to update the test status
        x, y = self.test_positions[test]

        # Update tests status
        logger.debug('Update test status (%s, %s), position (%d, %s)',
                     test, status.value, x, y)
        msg = self.formatted_test_status_str(test, status)
        TermOps.print_at(x, y, msg)
        self.restore_cursor_pos()

    def save_cursor_pos(self):
        self.cursor_pos = TermOps.get_cursor_pos()

    def restore_cursor_pos(self):
        TermOps.print_at(self.cursor_pos[0], self.cursor_pos[1], '\r')

    def finalize_test_positions(self):
        self.mvoe_up_position()
