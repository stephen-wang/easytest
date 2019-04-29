#!/usr/bin/python

import logging
import sys

from .logger import get_logger
from .resultmgr import TestResult
from .termops import MAX_ROWS, MAX_COLS, TermOps, TextColor


logger = get_logger('TermMgr', level=logging.DEBUG)


class TermMgr:
    """The util class for updating terminal output per test progress change"""

    _prompt_pos_ = None
    _RESULT_COLOR_MAPS_ = {
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

        self.max_path_len = max([len(p) for p in self.rel_test_paths])
        self.term_attr = None
        self.cursor_pos = None

    @classmethod
    def print_prompt(cls, msg):
        """Print out some prompt message"""

        # The first call will save current cursor position as Prompt Zone
        if cls._prompt_pos_ is None:
            cls.save_prompt_pos()

        # Save current cursor position
        oldx, oldy = TermOps.get_cursor_pos()

        # Print prompt message at Prompt Zone
        x, y = cls._prompt_pos_
        TermOps.print_at(x, y, msg)

        # Restore cursor position
        if (oldx, oldy) != (x, y):
            TermOps.print_at(oldx, oldy, '\r')

    def summarize(self, msg):
        """Print out the final summary of test result"""

        TermMgr.print_prompt('Testing is done')

        x, y = TermOps.get_cursor_pos()
        TermOps.print_at(x, y, msg, end='\n')

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

        return cls._RESULT_COLOR_MAPS_[test_result]

    def formatted_path_str(self, test_path):
        """Format test script path so that all scripts occupy same witdth and
        align to the right.
        """

        fmt = '\t{0: >%d}' % self.max_path_len
        formatted_path = fmt.format(test_path)
        return formatted_path

    def formatted_delimiter_str(self, test):
        """Return delimiter string between script path and test result"""

        return ' ' + '-' * int(MAX_COLS/2 - self.max_path_len) + ' '

    def formatted_status_str(self, status):
        """Format output string of test status"""

        color = self.test_result_color(status)
        colored_status = TermOps.colored_text(color, status.value)
        return '[' + colored_status + ']'

    def formatted_test_status_str(self, test, status, support_bundle=None):
        """Construct and return graceful output string like below:

               path/to/testscript1.py ------ [Running]
               path/to/testscript2.py ------ [Finished]
               path/to/testscript3.py ------ [Failed] --- /tmp/test_xx/xx.tar.gz
        """

        script_part = self.formatted_path_str(test)
        delim_part = self.formatted_delimiter_str(test)
        status_part = self.formatted_status_str(status)
        if status == TestResult.FAILED and support_bundle is not None:
            support_bundle_part = ' --- ' + support_bundle
        else:
            support_bundle_part = ''
        return script_part + delim_part + status_part + support_bundle_part

    def move_up_position(self):
        """Reduce the stored line number by 1 """

        # Adjust position of printed tests
        for script in self.test_positions.keys():
            oldx, oldy = self.test_positions[script];
            self.test_positions[script] = (oldx-1, oldy)

        TermMgr.move_up_prompt_position()

    @classmethod
    def move_up_prompt_position(cls):
        """Adjust position of Prompt Zone"""

        oldx, oldy = cls._prompt_pos_
        cls._prompt_pos_ = (oldx-1, oldy)  

    def print_test_status(self, test, status):
        """Print out test status to terminal, the position (row & line) where
        the info is printed is saved for later update.
        """ 
        
        logger.debug('Print test status (%s, %s)', test, status)

        # Get the position where to print the test status
        x, y = TermOps.get_cursor_pos()

        # Save the position where to print the information
        self.test_positions[test] = (x, y)

        # Format and output test status
        msg = self.formatted_test_status_str(test, status)
        TermOps.print_at(x, y, msg, end='\n') 

        # If the new line is at the bottom of terminal, all existing lines
        # should be moved 1 line up, thus we need to adjust the saved positions
        # accordingly.
        if x == MAX_ROWS:
            # If prompt zone is at bottom now, we need move it up explicitly
            if TermMgr._prompt_pos_[0] == MAX_ROWS:
                TermMgr.move_up_prompt_position()
            self.move_up_position()

        # Save current cursor position.
        self.save_cursor_pos()

    def update_test_status(self, test, status, support_bundle=None):
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

        # Update test status
        logger.debug('Update test status (%s, %s), position (%d, %s)',
                     test, status.value, x, y)
        msg = self.formatted_test_status_str(test, status, support_bundle)
        TermOps.print_at(x, y, msg)

        # Restore cursor position
        self.restore_cursor_pos()

    @classmethod
    def save_prompt_pos(cls):
        cls._prompt_pos_ = TermOps.get_cursor_pos()

    def save_cursor_pos(self):
        self.cursor_pos = TermOps.get_cursor_pos()

    def restore_cursor_pos(self):
        TermOps.print_at(self.cursor_pos[0], self.cursor_pos[1], '\r')
