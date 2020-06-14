#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import typing
import inspect
import functools

import bottle

from ..common import utils
from ..common import stamps

application = app = bottle.Bottle()
global_config = {}
global_objs = utils.AttrDict()


def _optional_type(t):
    if getattr(t, '__origin__', None) is not typing.Union:
        return None
    args = t.__args__
    if len(args) == 2 and args[1] is type(None):
        return args[0]
    return None


def convert_argument_type(args: dict, types: dict):
    for name, atype in types.items():
        opt_type = _optional_type(atype)
        value = args.get(name)
        if opt_type is not None:
            if value is None:
                continue
            atype = opt_type
        if atype is typing.Any:
            atype = lambda x: x
        if value is None:
            raise bottle.HTTPError(406, "parameter %s not found" % name)
        try:
            args[name] = atype(value)
        except Exception:
            raise bottle.HTTPError(
                406, "type of %s must be %s" % (name, atype.__name__))
    return args


def arg_type_hints(fn):
    arg_types = {}
    params_it = iter(inspect.signature(fn).parameters.items())
    for name, param in params_it:
        if param.annotation is inspect.Parameter.empty:
            arg_types[name] = typing.Any
        else:
            arg_types[name] = param.annotation
    return arg_types


def query_arguments(fn):
    """
    Decorator to parse and convert query arguments into function parameters.
    There are two usages:

    @query_arguments
    def get(self, id: int, name: Optional[str], value): ...
    # type hint is used. if no type hint, it's typing.Any

    The supported special types are typing.Optional and typing.Any.
    Use typing.Optional for None default value.
    Use typing.Any for no conversion, and it also has None as default value.
    """
    @functools.wraps(fn)
    def wrapped():
        atypes = arg_type_hints(fn)
        kwargs = convert_argument_type({
            name: bottle.request.params.get(name, None)
            for name in atypes
        }, atypes)
        print(kwargs)
        try:
            return fn(**kwargs)
        except TypeError as ex:
            raise bottle.HTTPError(406, ex.args[0])
    return wrapped


@app.route('/token', methods=('GET',))
@query_arguments
def route_token(host: str, ):
    ...


@app.route('/register', methods=('GET',))
@query_arguments
def route_register():
    ...


def initialize(config_path):
    global global_config, global_objs
    global_config = utils.load_config(config_path)
    key_config = utils.load_config(global_config['host']['key_pair'])
    global_objs['signer'] = stamps.Signer(key_config['key']['private'])
    key_store = stamps.IniKeyStore(global_config['scheduler']['worker_keys'])
    global_objs['verifier'] = stamps.Verifier(key_store)
