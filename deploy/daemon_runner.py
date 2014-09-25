from .pids import PIDFileManager
from .daemon import Daemon, DaemonException

import collections
import itertools

import time
import os
import psutil


MAX_WAIT_FOR_REGULAR_KILL = 10 # seconds

global hasproctitle
hasproctitle = False
try:
    import setproctitle
    hasproctitle = True
except ImportError:
    pass

class DaemonRunnerException(Exception):
    pass

class DaemonDefinition(object):
    def __init__(self, label, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.label = label

class ManagedDaemon(Daemon):
    def run(self, service_name, func, label, index, *args, **kwargs):
        global hasproctitle
        if hasproctitle:
            setproctitle.setproctitle('%s: %s.%u' % (service_name, label, index))

        print "Running %s.%u..." % (label, index)
        func(*args,**kwargs)
        print "Shutting down %s.%u..." % (label, index)

class DaemonRunner(object):
    def __init__(self, service_name, log_directory, user=None, group=None, pid_dir=None, umask=None):
        self._service_name = service_name

        if pid_dir is None:
            self._pid_manager = PIDFileManager(service_name)
        else:
            self._pid_manager = PIDFileManager(service_name, pid_dir)

        self._log_directory = log_directory
        # _working_processes is a set of psutil.Process object, that contains all the processes that are running on the daemon, including their children (recursively)
        # NOTE: for now it only updates when called to `stop` method
        self._working_processes = set()
        self._user = user
        self._umask = umask
        self._group = group

    def start(self,to_run):
        # Run all the daemons
        for i, ddef in enumerate(to_run):
            label,index,f = self._pid_manager.allocate_new(ddef.label)
            print "Starting daemon %s.%u (%u of %u)" % (label, index, i+1, len(to_run)) # Must put a newline or the fork does weird things in printing

            daemon_logfile = os.path.join(self._log_directory,'%s.%u-startup.log'%(label,index))
            d = ManagedDaemon(f, '/dev/null', daemon_logfile, daemon_logfile, [self._service_name, ddef.func, label, index]+list(ddef.args), ddef.kwargs, self._user, self._group, self._umask)

            try:
                d.start()
                time.sleep(1) # Let the daemon spin up (Because daemons might depend on one another)
            except DaemonException, e:
                raise DaemonRunnerException('Start failed for %s.%s: %s'%(label,index,e))

    def stop(self, include_children=False, max_wait_for_regular_kill=MAX_WAIT_FOR_REGULAR_KILL):
        """
        stops the processes.
        if include_children is true - waits for the children processes to die.
        if after max_wait_for_regular_kill seconds they didn't die - kills them brutally.
        """
        to_stop = self._pid_manager.get_all()

        # get all the pids
        parents_processes = _get_pids_as_processes(Daemon(file_path)._get_pid() for label, index, file_path in to_stop)
        children_processes = list(itertools.chain.from_iterable([proc.get_children(recursive=True) for proc in parents_processes]))

        # update all of the pids in self._working_processes
        self._working_processes.update([proc for proc in parents_processes + children_processes])

        # kill the parent processes
        for i, (label, index, f) in enumerate(to_stop):
            print "Stopping daemon %s.%u (%u of %u)" % (label, index, i+1, len(to_stop)) # Must put a newline or the fork does weird things in printing

            try:
                Daemon(f).stop() # Stop the daemon
            except DaemonException,e:
                raise DaemonRunnerException('Stop failed for %s.%s: %s'%(label,index,e)) 
        
        # killed all the parents - if we don't need to kill the children too (or there aren't any) - we can finish
        if not include_children or not children_processes:
            return

        # handle the children - if they're not dead after max_wait_for_regular_kill - kill all of them brutally
        print "waiting %d seconds for %d children processes to die" % (max_wait_for_regular_kill, len(children_processes))
        if not _processes_are_dead(children_processes, max_wait_for_regular_kill):
            print "children are not dead yet. stopping them.."
            for proc in children_processes:
                while proc.is_running():
                    # KILL them (and not only terminate) - because they were suppose to be dead after we killed their parents. those bastards.
                    print "killing process %d" % proc.pid
                    proc.kill()
                    time.sleep(0.1)
        else:
            print "children died in a natural way!"

    # No prints on verify, as it should be quick and have no side effects
    def verify(self,counts):
        found = collections.defaultdict(int)

        for label,index,f in self._pid_manager.get_all():
            if not Daemon(f).is_running():
                raise DaemonRunnerException('Verification failed: %s.%u is not running!'%(label,index))

            found[label] += 1

        for label in counts:
            if found[label] != counts[label]:
                raise DaemonRunnerException('Verification failed: %u %s running instead of %u'%(found[label],label,counts[label]))

    def verify_stopped(self):
        return len(self._pid_manager.get_all()) == 0 and all(not proc.is_running() for proc in self._working_processes)


def _get_pids_as_processes(pids):
    processes = []
    for pid in pids:
        if psutil.pid_exists(pid):
            processes.append(psutil.Process(pid))
        else:
            print "Warning: pid %s not found in system, although it is in the pid Manager" % pid
    return processes

def _processes_are_dead(processes, max_wait=MAX_WAIT_FOR_REGULAR_KILL):
    """
    waiting until max_wait for the processes to die (on their own).
    returns if the processes are dead after max_wait reaches (or if they're dead before)
    """
    wait_intervals = 0.2
    time_count = 0
    # simple polling
    # continue as long we didn't reach the max wait and there's still a process running
    while time_count <= max_wait and any(proc.is_running() for proc in processes):
        time.sleep(wait_intervals)
        time_count += wait_intervals
    # return True if all of the processes are dead (i.e not running)
    return all(not proc.is_running() for proc in processes)
