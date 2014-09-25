import os, os.path, glob, collections

class PIDFileManager(object):
    def __init__(self, service_name, pid_path='~/.pids'):
        self._pid_path = os.path.abspath(os.path.expanduser(pid_path))
        self._next_allocation_min = collections.defaultdict(int)
        self._service_name = service_name

    def get_all(self):
        """
        returns a list of 3-tuples: [(label, index, abs_path), ...]
        where label is the name of the process (e.g worker, brain, state, ...)
        index is the index of the process (e.g worker.0.pid, worker1.pid -> 0, 1)
        and abs_path is the absolute path of the pid file
        """
        out = []
        fnames = glob.glob(os.path.join(self._pid_path, '%s.*.pid' % self._service_name))

        for f in fnames:
            base = os.path.basename(f)
            abs_path = os.path.abspath(f)
            label, index = base.split('.')[1:3]

            index = int(index) # Parse the string
            out.append((label, index, abs_path))

        return out

    def allocate_new(self,label):
        # We have to have the dir to allocate a new path
        if not os.path.exists(self._pid_path):
            raise Exception('PID Path %s must exist!' % self._pid_path)

        all = self.get_all()
        this_label = [x for x in all if x[0] == label]

        if len(this_label) == 0:
            index = 0
        else:
            index = max([x[1] for x in this_label]) + 1 # Always grow the index, to help with debugging

        # This is to prevent allocating the same index in quick succession, before the processes got a chance to fork
        # So we make sure we never allocate numbers lower than we already have
        if index < self._next_allocation_min[label]:
            index = self._next_allocation_min[label]

        self._next_allocation_min[label] = index + 1 # Next time allocate atleast larger than this time

        path = os.path.join(self._pid_path,'%s.%s.%u.pid' % (self._service_name, label, index))
        return (label,index,os.path.abspath(path))