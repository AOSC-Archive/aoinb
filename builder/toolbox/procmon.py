#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess

import osutil


def systemd_show(unit):
    val_map = {'[not set]': None, '[no data]': None, 'yes': True, 'no': False}
    proc = subprocess.run(
        ('systemctl', 'show', unit), capture_output=True, check=True)
    result = {}
    for line in proc.stdout.decode().splitlines():
        name, value = line.split('=', 1)
        result[name] = val_map.get(value, value)
    return result


class ManagedProcess:
    wrapper_args = (
        'systemd-run', '--remain-after-exit', '--same-dir', '--nice=1',
        '--property=Type=exec',
        '--property=CPUAccounting=on', '--property=MemoryAccounting=on',
    )

    def __init__(self, args, logfile, cwd=None, sd_args=()):
        self.cwd = cwd or os.getcwd()
        self.logfile = os.path.abspath(logfile)
        cmd_args = list(self.wrapper_args)
        cmd_args.append('--property=StandardOutput=append:' + self.logfile)
        cmd_args.append('--property=StandardError=append:' + self.logfile)
        cmd_args.extend(sd_args)
        cmd_args.append('--')
        cmd_args.extend(args)
        print('Starting')
        try:
            proc = subprocess.run(
                cmd_args, capture_output=True, check=True, cwd=self.cwd)
        except subprocess.CalledProcessError as ex:
            print('error: %s' % ex.stdout)
            print(ex.stderr)
        print('Started: %s' % proc.stdout)
        print('Started: %s' % proc.stderr)
        self.unit = proc.stderr.strip().decode().rsplit(' ', 1)[-1]
        print('Started: %s' % self.unit)
        d = systemd_show(self.unit)
        self.start_mtn = int(d.get('ExecMainStartTimestampMonotonic') or 0)
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
        d = systemd_show(self.unit)
        result = d.get('CPUUsageNSec')
        if result:
            self.cpu_time = int(result)
        if d['SubState'] != 'running':
            self.exit_code = d['ExecMainStatus']
            stop_mtn = int(d.get('ExecMainExitTimestampMonotonic') or 0)
            self.real_time = (stop_mtn - self.start_mtn) * 1000
            self.cwd_size = osutil.directory_size(self.cwd)
            subprocess.run(('systemctl', 'stop', self.unit), check=True)
            return self.exit_code
        result = int(d.get('MemoryCurrent') or 0)
        if (self.max_mem or 0) < (result or 0):
            self.max_mem = result
        return None

    def kill(self):
        subprocess.run(('systemctl', 'kill', self.unit), check=True)

    def wait(self):
        with open(self.logfile, 'rb') as f:
            while self.poll() is None:
                try:
                    where = f.tell()
                    while True:
                        line = f.readline()
                        if line:
                            sys.stdout.buffer.write(line)
                        else:
                            break
                    sys.stdout.buffer.flush()
                    time.sleep(0.5)
                    f.seek(where)
                except KeyboardInterrupt:
                    self.kill()
        sys.stdout.buffer.flush()
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
    p = ManagedProcess(sys.argv[1:], 'log.txt')
    p.wait()
