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
        """The interval parameter defines time between each call to the function.
        """

        threading.Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.finished = threading.Event()

    def cancel(self):
        """Stop the roller."""

        self.finished.set()

    def run(self):

        while not self.finished.isSet():
            # self.finished.wait(self.interval)
            self.function(*self.args, **self.kwargs)


def endless_poll(child, screen):
    """This keeps the screen updated with the output of the child. This runs in
    a separate thread. See roller(). """

    try:
        s = child.read_nonblocking(4000, 0.1)
        screen.write(s)
    except:
        pass


class memtest86(object):

    """this class is to interact with memtest86"""

    def __init__(self, server, port):
        self.roller = None
        self.child = pexpect.spawn('telnet %s %s' % (server, port))
        r, c = self.child.getwinsize()
        self.crt = ANSI.ANSI(r, c)

    def start(self):
        # if this is a duplicate session, choose 1 option to enter
        if 0 == self.child.expect(["Enter your option : ", "Time: "]):
            print "enter duplicated session"
            self.crt.write(self.child.before)
            self.crt.write(self.child.after)
            self.child.send("1")

        self.roller = roller(0.1, endless_poll, (self.child, self.crt))
        self.roller.start()
        self.refresh()
        print "memtest86 started"
        print "----------------------------------------\n"

    def stop(self):
        if self.roller:
            self.roller.cancel()

        self.child.terminate()
        print "\n----------------------------------------"

    def refresh(self):
        self.child.send('c0')
        time.sleep(1)

    def dump(self):
        print str(self.crt)

    def get_region(self, rs, cs, re, ce):
        l = self.crt.get_region(rs, cs, re, ce)
        s = [ i.strip() for i in l]
        return '\n'.join(s)


    def print_sysinfo(self):
        version = self.get_region(1, 1, 1, 80)
        print version
        mem_info = self.get_region(2, 1, 6, 28)
        print mem_info


    


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
        test.print_sysinfo()
        test.dump()
    finally:
        test.stop()
        print "done!"

if __name__ == "__main__":

    try:
        main()
    except Exception, e:
        print str(e)
        tb_dump = traceback.format_exc()
        print str(tb_dump)
