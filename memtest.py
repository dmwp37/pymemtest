#!/usr/bin/env python

"""Memtest86 Python Wrapper for automation test

This suppose we open a telnet session over a console server for the DUT

    --hostname : the console server address.
    --port     : the connection port for the DUT
"""

import sys
import os
import getopt
import traceback
from memtest86 import *


def exit_with_usage(exit_code=1):
    print globals()['__doc__']
    os._exit(exit_code)


def print_test_result(summary, error):
    print "\r----------------------------------------"
    print summary
    print "----------------------------------------"
    if error != 0:
        print "test failed! Errors: %s" % error
    else:
        print "test passed"


def main():
    try:
        optlist, args = getopt.getopt(
            sys.argv[1:], 'h?', ['help', 'h', '?', 'hostname=', 'port='])
    except Exception, e:
        print str(e)
        exit_with_usage()

    options = dict(optlist)
    if [elem for elem in options if elem in ['-h', '--h', '-?', '--?', '--help']]:
        exit_with_usage(0)

    hostname = "10.208.12.12"
    port = 7018
    if '--hostname' in options:
        hostname = options['--hostname']
    if '--port' in options:
        port = int(options['--port'])

    try:
        test = memtest86(hostname, port)
        test.start()
        print "memtest86 started"
        print "----------------------------------------\n"
        print test.get_version()
        print "\nsystem memory information"
        print test.get_info()

        print "\nstart memory86 test"
        test.restart(1)
        old_round = ""
        old_test = ""
        old_progress = ""
        error = 0

        while True:
            # check test round
            r = test.get_current_round()
            if r and r != old_round:
                if "summary" in r:
                    # test finished here
                    error = int(test.get_errors())
                    summary = test.get_summary()
                    print_test_result(summary, error)
                    break
                else:
                    old_round = r
                    print "\r%s" % r

            # check test item
            t = test.get_current_test()
            if t and t != old_test:
                old_test = t
                print "\r%s" % t

            # check test progress
            p = "%s %s" % (test.get_test_progress(), test.get_time())
            if p != old_progress:
                old_progress = p
                sys.stdout.write("\r                \r%s" % p)
                sys.stdout.flush()

            time.sleep(0.2)
    finally:
        test.stop()


if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        print str(e)
        tb_dump = traceback.format_exc()
        print str(tb_dump)
