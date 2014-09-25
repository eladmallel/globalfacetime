#!/usr/bin/env python

import sys, os, time, atexit
HAS_USER_SUPPORT = False
try:
    from pwd import getpwnam
    from grp import getgrnam
    HAS_USER_SUPPORT = True
except ImportError:
    pass

from signal import SIGTERM

class DaemonException(Exception):
        pass

class Daemon(object):
        """
        A generic daemon class.

        Usage: subclass the Daemon class and override the run() method
        """
        def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null', args=(), kwargs={}, user=None, group=None, umask=None):
                self.stdin = stdin
                self.stdout = stdout
                self.stderr = stderr
                self.pidfile = pidfile
                self.args = args
                self.kwargs = kwargs
                self.user = user
                self.umask = umask
                self.group = group

        def daemonize(self):
                """
                do the UNIX double-fork magic, see Stevens' "Advanced
                Programming in the UNIX Environment" for details (ISBN 0201563177)
                http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16

                Returns False in the parent and True in the daemon
                """
                try:
                        pid = os.fork()
                        if pid > 0:
                                # Resume execution for the first parent
                                return False
                except OSError, e:
                        raise DaemonException("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))

                # decouple from parent environment
                os.chdir("/")
                os.setsid()
                os.umask(0)

                # do second fork
                try:
                        pid = os.fork()
                        if pid > 0:
                                # exit from second parent
                                sys.exit(0)
                except OSError, e:
                        raise DaemonException("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))

                # If a user or group is defined, switch to them
                # Must set group first, as after setting user we arent root
                if HAS_USER_SUPPORT:
                    if self.group is not None:
                        os.setgid(getgrnam(self.group).gr_gid)

                    if self.user is not None:
                        os.setuid(getpwnam(self.user).pw_uid)

                    if self.umask is not None:
                        os.umask(self.umask)


                # redirect standard file descriptors
                sys.stdout.flush()
                sys.stderr.flush()
                si = file(self.stdin, 'r')
                so = file(self.stdout, 'a+')
                se = file(self.stderr, 'a+', 0)
                os.dup2(si.fileno(), sys.stdin.fileno())
                os.dup2(so.fileno(), sys.stdout.fileno())
                os.dup2(se.fileno(), sys.stderr.fileno())

                # write pidfile
                atexit.register(self.delpid)
                pid = str(os.getpid())
                file(self.pidfile,'w+').write("%s\n" % pid)

                return True # As we are the daemon

        def delpid(self):
                try:
                        os.remove(self.pidfile)
                except OSError,e:
                        message = "Could not delete pidfile %s in delpid due to %s\n"
                        sys.stderr.write(message % (self.pidfile,e))
                        pass # If it wasn't removed, it isn't an error

        def _get_pid(self):
                # Check for a pidfile to see if the daemon already runs
                try:
                        pf = file(self.pidfile,'r')
                        pid = int(pf.read().strip())
                        pf.close()
                except IOError:
                        pid = None

                return pid

        def is_running(self):
                # Check for a pidfile to see if the daemon already runs
                pid = self._get_pid()

                if pid is None: # No pid? Not running
                        return False

                try:
                        os.kill(pid, 0) # Doesn't kill, just makes sure it exists
                        time.sleep(0.1)
                except OSError:
                        return False # Exception is raised if pid doesn't exist - so service doesn't exist

                return True # It is running

        def start(self):
                """
                Start the daemon
                """
                # Check for a pidfile to see if the daemon already runs
                if self._get_pid() is not None:
                        raise DaemonException("pidfile %s already exist. Daemon already running?\n")

                # Start the daemon
                if self.daemonize():
                        self.run(*self.args,**self.kwargs) # Will only run in the daemon process
                        sys.exit(0) # Done, no need to run the rest of the parent code

        def stop(self):
                """
                Stop the daemon
                """
                # Get the pid from the pidfile
                pid = self._get_pid()

                if not pid:
                        message = "pidfile %s does not exist. Daemon not running?\n"
                        sys.stderr.write(message % self.pidfile)
                        return # not an error in a restart

                # Try killing the daemon process
                try:
                        while 1:
                                os.kill(pid, SIGTERM)
                                time.sleep(0.1)
                except OSError, err:
                        err = str(err)
                        if err.find("No such process") > 0:
                                if os.path.exists(self.pidfile):
                                        os.remove(self.pidfile)
                        else:
                                raise DaemonException(str(err))

        def restart(self):
                """
                Restart the daemon
                """
                self.stop()
                self.start()

        def run(self):
                """
                You should override this method when you subclass Daemon. It will be called after the process has been
                daemonized by start() or restart().
                """