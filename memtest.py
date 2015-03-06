#!/usr/bin/env python

"""Memtest86 Python Wrapper for automation test

This suppose we open a telnet session over a console server for the DUT

    --hostname : the console server address.
    --port     : the connection port for the DUT
"""

import pexpect
import ANSI
import time
import sys
import os
import getopt
import traceback
import threading


def exit_with_usage(exit_code=1):

    print globals()['__doc__']
    os._exit(exit_code)


class roller (threading.Thread):

    """This runs a function in a loop in a thread."""

    def __init__(self, interval, function, args=[], kwargs={}):
        """The interval parameter defines time between each call to the function."""
        threading.Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.finished = threading.Event()

    def cancel(self):
        self.finished.set()

    def run(self):

        while not self.finished.isSet():
            # self.finished.wait(self.interval)
            self.function(*self.args, **self.kwargs)


class memtest86(object):

    """this class is to interact with memtest86"""

    def __init__(self, server, port):
        self.roller = None
        self.child = pexpect.spawn('telnet %s %s' % (server, port))
        r, c = self.child.getwinsize()
        self.crt = ANSI.ANSI(r, c)

    def _update_crt(self):
        """This keeps the screen updated with the output of the child. This runs in
        a separate thread. See roller(). """
        try:
            buf = self.child.read_nonblocking(4000, 0.1)
            self.crt.write(buf)
        except:
            pass

    def start(self):
        """Start to monitor the remote memtest86"""
        # if this is a duplicate session, choose option 1 to enter
        if 0 == self.child.expect(["Enter your option : ", "Time: "]):
            print "enter duplicated session"
            self.crt.write(self.child.before)
            self.crt.write(self.child.after)
            self.child.send("1")

        self.roller = roller(0.1, self._update_crt)
        self.roller.start()
        self.refresh()

    def stop(self):
        """Stop to monitor the remote memtest86"""
        if self.roller:
            self.roller.cancel()

        self.child.terminate()

    def refresh(self):
        """refresh the crt so that we can get full data"""
        self.child.send('c0')
        while "DDR3" not in self.get_info():
            time.sleep(0.1)

    def restart(self):
        """restart the memtest86 from beginning"""
        self.child.send('c3s')
        while "Test 0" not in self.get_current_test():
            time.sleep(0.1)

    def reboot(self):
        """exit memtest86 and reboot the DUT"""
        self.child.send('')
        time.sleep(1)

    def dump(self):
        """dump the crt screen"""
        print str(self.crt)

    def config(self):
        """config the remote memtest86"""
        pass

    def get_region(self, rs, cs, re, ce):
        """retrieve the strings from crt screen region"""
        l = self.crt.get_region(rs, cs, re, ce)
        s = [i.strip() for i in l]
        return '\n'.join(s)

    def get_version(self):
        """retrieve the version string"""
        return self.get_region(1, 1, 1, 80)

    def get_info(self):
        """retrieve the memory information"""
        return "\n".join((self.get_region(2, 1, 6, 28),
                          self.get_region(7, 1, 7, 80)))

    def get_time(self):
        """retrieve the total test running time"""
        return self.get_region(12, 6, 12, 16)

    def get_errors(self):
        """retrieve the total test errors"""
        return self.get_region(12, 73, 12, 80)

    def get_cpus(self):
        """retrieve the total available cpu number"""
        return self.get_region(9, 53, 9, 80)

    def get_current_pass(self):
        """retrieve the current test round"""
        return self.get_region(12, 40, 12, 65)

    def get_current_test(self):
        """retrieve the current test item"""
        return self.get_region(4, 30, 4, 80)

    def get_test_progress(self):
        """retrieve the current test progress"""
        return self.get_region(3, 35, 3, 40)

    def get_pass_progress(self):
        """retrieve the current round test progress"""
        return self.get_region(2, 30, 2, 80)


def main():

    try:
        optlist, args = getopt.getopt(
            sys.argv[1:], 'h?', ['help', 'h', '?', 'hostname=', 'port='])
    except Exception, e:
        print str(e)
        exit_with_usage()

    options = dict(optlist)
    # There are a million ways to cry for help. These are but a few of them.
    if [elem for elem in options if elem in ['-h', '--h', '-?', '--?', '--help']]:
        exit_with_usage(0)

    hostname = "10.208.12.12"
    port = 7018
    if '--hostname' in options:
        hostname = options['--hostname']
    if '--port' in options:
        port = int(options['--port'])

    test = memtest86(hostname, port)
    try:
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
