#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import bottle

from . import base
from ..common import utils

application = app = bottle.Bottle()
global_config = {}
global_objs = utils.AttrDict()


class PollHandler(base.BaseHandler):
    route = '/poll'

    def post(self):
        return {'result': 'ok'}


HANDLERS = [PollHandler]


def initialize(app, config):
    base.BaseHandler.initialize(config)
    base.ErrorHandler.register(app)
    for handler in HANDLERS:
        handler.register(app)
