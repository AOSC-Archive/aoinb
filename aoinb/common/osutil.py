#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import socket
import hashlib
import pathlib
import platform


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def touch(filename):
    pathlib.Path(filename).touch()


def hashtag(s, length=8):
    return hashlib.blake2b(s, digest_size=length).hexdigest()


def machine_id():
    with open('/etc/machine-id', 'rb') as f:
        idtag = hashtag(f.read(), 4)
    return '%s-%s' % (socket.gethostname(), idtag)


def same_device(a, b):
    return os.stat(a).st_dev == os.stat(b).st_dev


def copy_dir_tree(a, b, hardlink=True):
    if hardlink and same_device(a, b):
        shutil.copytree(a, b, symlinks=True, copy_function=os.link)
    else:
        shutil.copytree(a, b, symlinks=True)


def directory_size(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for name in files:
            try:
                stat = os.stat(os.path.join(root, name), follow_symlinks=False)
            except OSError:
                continue
            total += stat.st_size
    return total


def get_arch_name():
    """
    Detect architecture of the host machine

    :returns: architecture name
    """
    uname_var = platform.machine() or platform.processor()
    if uname_var in ['x86_64', 'amd64']:
        return 'amd64'
    elif uname_var == 'aarch64':
        return 'arm64'  # FIXME: Don't know ...
    elif uname_var in ['armv7a', 'armv7l', 'armv8a', 'armv8l']:
        return 'armel'    # FIXME: Don't know too much about this...
    elif uname_var == 'mips64':
        return 'mips64el'  # FIXME: How about big endian...
    elif uname_var == 'mips':
        return 'mipsel'   # FIXME: This too...
    elif uname_var == 'ppc':
        return 'powerpc'
    elif uname_var == 'ppc64':
        return 'ppc64'
    elif uname_var == 'riscv64':
        return 'riscv64'
    else:
        return None
    return None


