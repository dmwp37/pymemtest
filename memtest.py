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
        test.restart()
        old_round = ""
        old_test = ""
        old_progress = ""
        while True:
            # check errors
            e = int(test.get_errors())
            if e != 0:
                print "error happened!"
                break

            # check test round
            r = test.get_current_pass()
            if r != old_round:
                old_round = r
                print "\r%s" % r

            # check test item
            t = test.get_current_test()
            # check finish condition
            if "Test 3" in t:
                sys.stdout.write("\r")
                break

            if t != old_test:
                old_test = t
                print "\r%s" % t

            # check test progress
            p = test.get_test_progress()
            if p != old_progress:
                old_progress = p
                sys.stdout.write("\r    \r%s" % test.get_test_progress())
                sys.stdout.flush()

            time.sleep(0.1)
    finally:
        test.stop()
        print "----------------------------------------"
        print "time used: %s\n" % test.get_time()
        error = int(test.get_errors())
        if error != 0:
            print "test failed! Errors: %s" % test.get_errors()
        else:
            print "test passed"


if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        print str(e)
        tb_dump = traceback.format_exc()
        print str(tb_dump)
