#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import lxml.etree
import collections

RE_PACKAGE = re.compile(r'^(.+?)-(?:ch\w+-)?sbu$')
RE_SBU = re.compile(r'([0-9.]+) SBU')

sbus = collections.OrderedDict()

with open(sys.argv[1], 'rb') as f:
    tree = lxml.etree.DTD(f)
    for ent in tree.entities():
        match = RE_PACKAGE.match(ent.name)
        if match is None:
            continue
        sbus[match.group(1)] = RE_SBU.search(ent.content).group(1)

for key, value in sbus.items():
    print('%s,%s' % (key, value))
