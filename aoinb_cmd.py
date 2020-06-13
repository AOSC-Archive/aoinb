#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import aoinb.commands


def main(cmd_args):
    parser = argparse.ArgumentParser(
        description="AOINB: Next-generation distributed build system")
    parser.add_argument("-c", "--config", help="config file")
    subparsers = parser.add_subparsers(
        dest='subcommand', help='sub-command help')
    p_build = subparsers.add_parser('build', help='Build specified packages')
    p_build.add_argument("package", nargs="+", help='package names')
    subparsers.add_parser('genkey', help='Generate a key pair')
    args = parser.parse_args(cmd_args)
    if args.subcommand:
        getattr(aoinb.commands, 'cmd_' + args.subcommand)(args)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
