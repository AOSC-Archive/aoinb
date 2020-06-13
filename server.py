#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test server or WSGI entry point.
"""

import sys
from aoinb.scheduler.http_server import app, application


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 8082
    if len(sys.argv) > 1:
        srvhost = sys.argv[1]
        spl = srvhost.rsplit(":", 1)
        if spl[1].isnumeric():
            host = spl[0].lstrip('[').rstrip(']')
            port = int(spl[1])
        else:
            host = srvhost.lstrip('[').rstrip(']')
    app.run(host=host, port=port, server='auto')

