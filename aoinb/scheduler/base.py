#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import bottle
import inspect
import typing
import functools
import typeguard
from ..common import utils
from ..common import stamps


def _optional_type(t):
    if getattr(t, '__origin__', None) is not typing.Union:
        return None
    args = t.__args__
    if len(args) == 2 and args[1] is type(None):
        return args[0]
    return None


def check_argument_type(args: dict, types: dict):
    for name, atype in types.items():
        value = args.get(name)
        if value is None:
            args[name] = None
        try:
            typeguard.check_type(name, value, atype)
        except TypeError as e:
            raise bottle.HTTPError(406, str(e))


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
        try:
            return fn(**kwargs)
        except TypeError as ex:
            raise bottle.HTTPError(406, ex.args[0])
    return wrapped


def body_arguments(fn):
    """
    Decorator to parse and check body arguments.

    @body_arguments
    def post(self, id: int, name: Optional[str], value): ...
    # type hint is used. if no type hint, it's typing.Any

    All typing checks are available.
    """

    @functools.wraps(fn)
    def wrapped():
        try:
            kwargs = json.load(bottle.request.body)
        except json.JSONDecodeError:
            raise bottle.HTTPError(406, "invalid JSON")
        check_argument_type(kwargs, arg_type_hints(fn))
        try:
            return fn(**kwargs)
        except TypeError as ex:
            raise bottle.HTTPError(406, ex.args[0])
    return wrapped


class BaseHandler:
    # config file
    global_config = None
    global_objs = None

    # bottle rule path
    route = None

    def __init__(self, app):
        self.app = app
        self.current_machine = None

    @classmethod
    def initialize(cls, config):
        """
        Initialize the global config for the app.
        """
        cls.global_config = config
        key_config = utils.load_config(config['host']['key_pair'])
        key_store = stamps.IniKeyStore(
            config['scheduler']['worker_keys'])
        cls.global_objs = utils.AttrDict(
            signer=stamps.Signer(key_config['key']['private']),
            verifier=stamps.Verifier(key_store)
        )

    @classmethod
    def callback_fn(cls, app, method):
        handler = cls(app)
        callback = getattr(handler, method.lower())

        def wrapper(*args, **kwargs):
            handler.prepare(method)
            try:
                response = callback(*args, **kwargs)
            finally:
                handler.close(method)
            return response
        return wrapper

    @classmethod
    def register(cls, app):
        for method in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'):
            if not hasattr(cls, method.lower()):
                continue
            app.add_route(bottle.Route(
                app, cls.route, method, cls.callback_fn(app, method)
            ))

    def prepare(self, method):
        pass

    def close(self, method):
        pass


class ErrorHandler(BaseHandler):
    default_codes = (403, 404, 406, 409)

    @classmethod
    def callback_fn(cls, app, code, callback=None):
        handler = cls(app)
        if callback is None:
            return getattr(handler, 'err_%s' % code)
        return callback

    @classmethod
    def register(cls, app):
        for func in dir(cls):
            if func == 'default':
                for code in cls.default_codes:
                    app.error(code=code)(cls(app).default)
            elif not func.startswith('err_'):
                continue
            else:
                code = int(func[4:])
                app.error(code=code)(cls.callback_fn(app, code))

    def default(self, error):
        bottle.response.content_type = 'application/json'
        return json.dumps({'status': error.status, 'msg': error.body})


class AutoArgumentsMixin:
    @classmethod
    def callback_fn(cls, app, method):
        handler = cls(app)
        callback = getattr(handler, method.lower())
        if method in ('GET', 'DELETE'):
            callback = query_arguments(callback)
        else:
            callback = body_arguments(callback)

        def wrapper(*args, **kwargs):
            handler.prepare(method)
            try:
                response = callback(*args, **kwargs)
            finally:
                handler.close(method)
            return response
        return wrapper


class BaseAPIHandler(AutoArgumentsMixin, BaseHandler):
    signature_ttl = 300

    def prepare(self, method):
        if method not in ('POST', 'PUT', 'PATCH'):
            return
        machine = bottle.request.get_header('X-Machine', '')
        signature = bottle.request.get_header('X-Signature', '')
        if not self.global_objs.verifier.verify(
            machine, bottle.request.body, signature, self.signature_ttl):
            raise bottle.HTTPError(403, 'invalid signature')
