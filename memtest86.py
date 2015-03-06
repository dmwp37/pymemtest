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


if __name__ == "__main__":
    print globals()['__doc__']
