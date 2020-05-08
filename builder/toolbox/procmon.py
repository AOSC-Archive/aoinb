#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess
import collections

import psutil
import osutil

if sys.version_info < (3, 7):
    time.time_ns = lambda x: int(time.time() * 1e9)
    time.monotonic_ns = lambda x: int(time.monotonic() * 1e9)


class ProcessStats(collections.namedtuple(
    'ProcessStats', ('memory', 'cpu_sys', 'cpu_user'))):
    def __add__(self, other):
        return type(self)(
            self.memory + other.memory,
            self.cpu_sys + other.cpu_sys,
            self.cpu_user + other.cpu_user,
        )


def get_process_stats(proc):
    try:
        with proc.oneshot():
            cpu_times = proc.cpu_times()
            mem_info = proc.memory_full_info()
        return ProcessStats(
            mem_info.uss,
            int(cpu_times.system * 1e9),
            int(cpu_times.user * 1e9)
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def get_all_process_stats(pid):
    
    try:
        proc = psutil.Process(pid)
        stats = get_process_stats(proc) or ProcessStats(0, 0, 0)
        for subproc in proc.children(recursive=True):
            result = get_process_stats(subproc)
            if result:
                stats += result
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None
    return stats


class ManagedProcess:
    def __init__(self, args, logfile, cwd=None, sd_args=()):
        self.cwd = cwd or os.getcwd()
        self.logfile = os.path.abspath(logfile)
        self.proc = subprocess.Popen(
            args, cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        self.start_mtn = time.monotonic_ns()
        self.max_mem = None
        self.cpu_time = None
        self.real_time = None
        self.exit_code = None
        self.cwd_size = None

    @property
    def parallel_rate(self):
        if all((self.cpu_time, self.real_time)):
            return max(0, (self.cpu_time/self.real_time - 1))
        return None

    def poll(self):
        poll_time = time.monotonic_ns()
        self.exit_code = self.proc.poll()
        if self.exit_code is not None:
            self.real_time = (poll_time - self.start_mtn)
            self.cwd_size = osutil.directory_size(self.cwd)
            return self.exit_code
        res = get_all_process_stats(self.proc.pid)
        if not res:
            return None
        self.cpu_time = res.cpu_sys + res.cpu_user
        if (self.max_mem or 0) < res.memory:
            self.max_mem = res.memory
        return None

    def kill(self):
        self.proc.terminate()
        try:
            self.proc.wait(1)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.poll()

    def wait(self):
        with open(self.logfile, 'wb') as f:
            while self.poll() is None:
                try:
                    line = self.proc.stdout.readline()
                    if line:
                        sys.stdout.buffer.write(line)
                        f.write(line)
                    else:
                        break
                    sys.stdout.buffer.flush()
                except KeyboardInterrupt:
                    self.kill()
        self.poll()
        sys.stdout.buffer.flush()

    def print_summary(self):
        print('')
        print('='*20)
        print('Exit code: %s' % self.exit_code)
        if self.max_mem:
            print('Max memory usage: %s' % osutil.sizeof_fmt(self.max_mem))
        if self.cpu_time:
            print('CPU time: %.3fs' % (self.cpu_time / 1e9))
        if self.real_time:
            print('Total time: %.3fs' % (self.real_time / 1e9))
        prate = self.parallel_rate
        if prate is not None:
            print('Parallel rate: %.3f' % prate)
        print('Disk usage: %s' % osutil.sizeof_fmt(self.cwd_size))


if __name__ == '__main__':
    p = ManagedProcess(sys.argv[1:], 'log2.txt')
    p.wait()
    p.print_summary()
