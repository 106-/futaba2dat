import sys
from types import ModuleType


class _Object:
    @staticmethod
    def fromEntries(entries):
        return dict(entries)


class _Console:
    @staticmethod
    def log(_record):
        pass

    @staticmethod
    def warn(_record):
        pass

    @staticmethod
    def error(_record):
        pass


class _AbortSignal:
    @staticmethod
    def timeout(_milliseconds):
        return type("Signal", (), {"aborted": False})()


class _WebApi:
    @staticmethod
    def new(*_args, **_kwargs):
        raise RuntimeError("Cloudflare Web API is unavailable in CPython tests")


js = ModuleType("js")
js.AbortSignal = _AbortSignal
js.Object = _Object
js.Request = _WebApi
js.Response = _WebApi
js.caches = None
js.console = _Console
sys.modules.setdefault("js", js)
