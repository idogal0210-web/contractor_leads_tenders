"""
Shim for structlog using standard library logging when structlog is not installed.
Allows all modules to run out-of-the-box in local environments.
"""
import logging

class StandardLoggerAdapter:
    def __init__(self, logger, bound_kwargs=None):
        self._logger = logger
        self._bound_kwargs = bound_kwargs or {}

    def bind(self, **kwargs):
        new_kwargs = {**self._bound_kwargs, **kwargs}
        return StandardLoggerAdapter(self._logger, new_kwargs)

    def _fmt(self, event, kwargs):
        merged = {**self._bound_kwargs, **kwargs}
        return f"{event} {merged if merged else ''}"

    def info(self, event, **kwargs):
        self._logger.info(self._fmt(event, kwargs))

    def warning(self, event, **kwargs):
        self._logger.warning(self._fmt(event, kwargs))

    def error(self, event, **kwargs):
        self._logger.error(self._fmt(event, kwargs))

    def debug(self, event, **kwargs):
        self._logger.debug(self._fmt(event, kwargs))

def get_logger(name=None):
    logger = logging.getLogger(name or "leads_system")
    return StandardLoggerAdapter(logger)
