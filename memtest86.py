#!/usr/bin/env python

"""Memtest86 Class Python Wrapper

   The class use pexpect.ANSI to emulate the crt screen of telnet
   session and scrabe the data from it. Also we can use pexpect to
   interact with memtest86 thus manipulate it as if we sit in front.
"""

import pexpect
import ANSI
import time
import threading


KEY_UP = '\x1b[A'
KEY_DOWN = '\x1b[B'
KEY_RIGHT = '\x1b[C'
KEY_LEFT = '\x1b[D'
KEY_ENTER = '\r'

TOTAL_TEST = 11


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

    test_name = ["Test 0 [Address test, walking ones, 1 CPU]",
                 "Test 1 [Address test, own address, 1 CPU]",
                 "Test 2 [Address test, own address]",
                 "Test 3 [Moving inversions, ones & zeroes]",
                 "Test 4 [Moving inversions, 8-bit pattern]",
                 "Test 5 [Moving inversions, random pattern]",
                 "Test 6 [Block move, 64-byte blocks]",
                 "Test 7 [Moving inversions, 32-bit pattern]",
                 "Test 8 [Random number sequence]",
                 "Test 9 [Modulo 20, ones & zeros]",
                 "Test 10 [Bit fade test, two patterns, 1 CPU]"]

    def __init__(self, server, port):
        self.roller = None
        self._is_finish = False
        self.tests = set(range(TOTAL_TEST))
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

    def send_key(self, key):
        self.child.send(key)
        time.sleep(0.5)

    def start(self):
        """Start to monitor the remote memtest86"""
        # if this is a duplicate session, choose option 1 to enter
        if 0 == self.child.expect(["Enter your option : ", pexpect.TIMEOUT], timeout=3):
            print "enter duplicated session"
            self.crt.write(self.child.before)
            self.crt.write(self.child.after)
            self.send_key('1')

        # start the memtest86
        n = 0
        while 0 != self.child.expect(["Time: ", pexpect.TIMEOUT], timeout=2):
            self.send_key('s')
            self.send_key(KEY_LEFT)
            self.send_key(KEY_ENTER)
            n += 1
            if n > 5:
                raise ValueError("can't start memtest86!")

        self.roller = roller(0.1, self._update_crt)
        self.roller.start()
        self.refresh()

    def stop(self):
        """Stop to monitor the remote memtest86"""
        if self.roller:
            self.roller.cancel()

        self.child.terminate()

    def get_summary(self):
        """finish test return the report and reboot"""
        self.roller.cancel()
        time.sleep(0.2)
        self.crt.erase_screen()
        self.child.expect('.*', timeout=0.1)
        self.send_key(' ')
        self.child.expect('<Save.*>')
        s = self.child.before
        self.send_key('n')
        self.send_key('x')
        return s

    def refresh(self):
        """refresh the crt so that we can get full data"""
        time.sleep(1)  # wait all the data consummed
        self.crt.erase_screen()
        self.send_key('c')
        self.send_key('0')
        while "DDR3" not in self.get_info():
            time.sleep(0.1)

    def restart(self, round, test_set=range(TOTAL_TEST)):
        """restart the memtest86 from beginning
           pass in test rounds and test sets
        """
        self._config(round, test_set)
        time.sleep(1)
        self.send_key('s')
        self.crt.erase_screen()
        # wait till the test start
        while True:
            if "Pass:     1" not in self.get_current_round() or \
               "Test 0" not in self.get_current_test():
                time.sleep(0.1)
            else:
                break

    def reboot(self):
        """exit memtest86 and reboot the DUT"""
        self.send_key('c')
        self.send_key('3')
        self.send_key('x')

    def dump(self):
        """dump the crt screen"""
        print str(self.crt)

    def _config(self, passes, test_set):
        """config the remote memtest86"""
        # enable all the cpus
        self.send_key('c')
        self.send_key('3')
        self.send_key('c')
        self.send_key(KEY_DOWN)
        self.send_key(KEY_ENTER)
        # set the test item
        self.send_key('t')
        for i in range(TOTAL_TEST):
            # set the item
            if i in test_set:
                if i not in self.tests:
                    self.send_key(KEY_ENTER)
                    self.tests.add(i)
            # clear the item
            else:
                if i in self.tests:
                    self.send_key(KEY_ENTER)
                    self.tests.remove(i)
            # move to next item
            self.send_key(KEY_DOWN)

        # set the test passes
        self.send_key(KEY_ENTER)
        self.send_key(str(passes))
        self.send_key(KEY_ENTER)

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

    def get_current_round(self):
        """retrieve the current test round"""
        r = self.get_region(12, 40, 12, 65)
        if "| " in r:
            return ""
        if len(r) < 20:
            return ""
        if "Pass:     0" in r:
            return ""
        if "summary" in r:
            self._is_finish = True
            return ""
        return r

    def get_current_test(self):
        """retrieve the current test item"""
        # we need to return the full description
        t = self.get_region(4, 30, 4, 80)
        for i in self.test_name:
            if i[0:7] in t:
                return i
        return ""

    def get_test_progress(self):
        """retrieve the current test progress"""
        return self.get_region(3, 35, 3, 40)

    def get_pass_progress(self):
        """retrieve the current round test progress"""
        return self.get_region(2, 30, 2, 80)

    def is_finished(self):
        """retrieve if test finished"""
        return self._is_finish


if __name__ == "__main__":
    print globals()['__doc__']
