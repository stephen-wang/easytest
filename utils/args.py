#!/usr/bin/python3

import argparse

from .exceptions import InvalidArgumentError


def validate_args(args):
    if args.test is None and args.group is None:
        raise InvalidArgumentError('No --test or --group was provided')

    if args.test is not None and args.group is not None:
        raise InvalidArgumentError('--test and --group can\'t be used together')


def get_args():
    """Construct and return supported arguments"""

    desc = 'run.py is the entry point of easytest frameworkt'
    argparser = argparse.ArgumentParser(description=desc)

    argparser.add_argument('-t', '--test', help='The test to be run, which is '\
                           'mutually exclusive from --group', action='append')
    argparser.add_argument('-g', '--group', help='The test group to be run',
                           action='append')
    argparser.add_argument('-s', '--server', help='The test machine to run the '\
                           'tests', action='append', required=True)

    args = argparser.parse_args()
    validate_args(args)

    return args
